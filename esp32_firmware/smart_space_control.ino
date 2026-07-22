/*
  智能空间控制系统 v3.0 - ESP32 固件

  功能模块：
    - DHT11 温湿度传感器 (GPIO21)
    - 继电器控制 (GPIO27)
    - 光敏传感器 (GPIO34, ADC)
    - 光遮断传感器 (GPIO32) - 替代PIR
    - 有源蜂鸣器 (GPIO25)
    - OLED 显示 (GPIO18/19, I2C 0x3C)

  MQTT 主题：
    发布 esp32/sensors  → 温湿度 + 亮度 + 人体感应
    发布 esp32/status   → 设备状态
    订阅 esp32/control  → 控制指令
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// === WiFi 配置（上传前请修改）===
const char* ssid = "YOUR_WIFI_SSID";
const char* pass = "YOUR_WIFI_PASSWORD";

// === MQTT 配置 ===
const char* mqtt_server = "YOUR_SERVER_IP";
const int mqtt_port = 1883;
char mqtt_client_id[32];

// === 主题 ===
const char* topic_sensors = "esp32/sensors";
const char* topic_control = "esp32/control";
const char* topic_status  = "esp32/status";

// === GPIO ===
#define DHT_PIN    21
#define DHT_TYPE   DHT11
#define RELAY_PIN  27
#define LIGHT_PIN  34
#define PIR_PIN    32
#define BUZZER_PIN 25

// === OLED ===
#define SCREEN_W 128
#define SCREEN_H 64
#define OLED_RST -1
Adafruit_SSD1306 oled(SCREEN_W, SCREEN_H, &Wire, OLED_RST);

// === 全局对象 ===
WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(DHT_PIN, DHT_TYPE);

// === 状态 ===
unsigned long lastSend = 0;
const unsigned long SEND_INTERVAL = 2000;
bool relayState = false;
bool lastMotion = false;

// === 蜂鸣器 ===
bool buzzerOn = false;
unsigned long buzzerStart = 0;
const unsigned long BUZZER_MS = 500;

void buzzerBeep(unsigned long ms)
{
  buzzerOn = true;
  buzzerStart = millis();
  digitalWrite(BUZZER_PIN, HIGH);
  Serial.println("[Buzzer] beep!");
}

void updateBuzzer()
{
  if (buzzerOn && millis() - buzzerStart > BUZZER_MS)
  {
    buzzerOn = false;
    digitalWrite(BUZZER_PIN, LOW);
  }
}

// === 发布状态 ===
void publishStatus()
{
  char p[128];
  snprintf(p, sizeof(p),
    "{\"device_id\":\"%s\",\"relay\":%s,\"online\":true,\"ts\":%lu}",
    mqtt_client_id, relayState ? "true" : "false", millis());
  mqtt.publish(topic_status, p);
}

// === OLED 显示 ===
void updateOLED(float t, float h, int light, bool motion)
{
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  // 第一行：标题
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print(F("Smart Space v3.0"));

  // 第二行：温湿度
  oled.setCursor(0, 12);
  oled.print(F("T:"));
  oled.print(t, 1);
  oled.print(F("C  H:"));
  oled.print(h, 0);
  oled.print(F("%"));

  // 第三行：亮度 + 人体感应
  oled.setCursor(0, 24);
  int pct = map(light, 0, 4095, 0, 100);
  oled.print(F("Light:"));
  oled.print(pct);
  oled.print(F("% "));
  oled.print(motion ? F("[!]Motion") : F("    -"));

  // 第四行：MQTT状态
  oled.setCursor(0, 36);
  oled.print(mqtt.connected() ? F("MQTT: OK") : F("MQTT: Lost"));

  // 第五行：继电器状态
  oled.setCursor(0, 48);
  oled.print(F("Relay:"));
  oled.print(relayState ? F("ON ") : F("OFF"));

  oled.display();
}

// === 发布传感器数据 ===
void publishSensors()
{
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  int light = analogRead(LIGHT_PIN);
  bool motion = digitalRead(PIR_PIN);

  // 更新OLED显示
  updateOLED(t, h, light, motion);

  if (t > 35.0 && !isnan(t))
  {
    buzzerBeep(1000);
  }

  if (motion != lastMotion)
  {
    lastMotion = motion;
    publishStatus();
  }

  char p[256];
  snprintf(p, sizeof(p),
    "{\"device_id\":\"%s\",\"temp\":%.1f,\"hum\":%.1f,\"light\":%d,\"motion\":%s,\"relay\":%s,\"ts\":%lu}",
    mqtt_client_id, t, h, light,
    motion ? "true" : "false",
    relayState ? "true" : "false", millis());

  mqtt.publish(topic_sensors, p);

  Serial.print("[传感器] ");
  Serial.print(t);
  Serial.print("C  ");
  Serial.print(h);
  Serial.print("%  light=");
  Serial.print(light);
  Serial.print("  motion=");
  Serial.println(motion ? "YES" : "NO");
}

// === MQTT 回调 ===
void onMqttMessage(char* topic, byte* payload, unsigned int length)
{
  char buf[256];
  unsigned int len = length < sizeof(buf) - 1 ? length : sizeof(buf) - 1;
  memcpy(buf, payload, len);
  buf[len] = '\0';

  Serial.print("[MQTT] ");
  Serial.println(buf);

  String msg = String(buf);

  int cmdStart = msg.indexOf("\"command\"");
  if (cmdStart != -1)
  {
    cmdStart = msg.indexOf(":", cmdStart);
    if (cmdStart != -1)
    {
      int valStart = msg.indexOf("\"", cmdStart);
      if (valStart != -1)
      {
        int valEnd = msg.indexOf("\"", valStart + 1);
        if (valEnd != -1)
        {
          String cmd = msg.substring(valStart + 1, valEnd);
          if (cmd == "on")
          {
            digitalWrite(RELAY_PIN, HIGH);
            relayState = true;
            Serial.println("[Relay] ON");
          }
          else if (cmd == "off")
          {
            digitalWrite(RELAY_PIN, LOW);
            relayState = false;
            Serial.println("[Relay] OFF");
          }
        }
      }
    }
  }

  if (msg.indexOf("\"beep\"") != -1)
  {
    buzzerBeep(500);
  }

  publishStatus();
}

// === MQTT 连接 ===
void connectMqtt()
{
  while (!mqtt.connected())
  {
    Serial.print("[MQTT] connecting...");
    if (mqtt.connect(mqtt_client_id))
    {
      Serial.println(" OK!");
      static int retryDelay = 5000;
      retryDelay = 5000;
      mqtt.subscribe(topic_control);
      publishStatus();
    }
    else
    {
      Serial.print(" rc=");
      Serial.println(mqtt.state());
      // 退避重连：5s -> 10s -> 15s 循环
      static int retryDelay = 5000;
      delay(retryDelay);
      retryDelay = retryDelay >= 15000 ? 5000 : retryDelay + 5000;
    }
  }
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(mqtt_client_id, sizeof(mqtt_client_id),
    "ESP32_%02X%02X%02X%02X", mac[2], mac[3], mac[4], mac[5]);

  Serial.println("\n=== Smart Space Control v3.0 ===");
  Serial.print("Client ID: ");
  Serial.println(mqtt_client_id);

  dht.begin();

  // OLED初始化 (指定I2C引脚 GPIO18=SDA, GPIO19=SCL)
  Wire.begin(18, 19);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C))
  {
    Serial.println("[OLED] Failed! Check I2C wiring.");
  }
  else
  {
    oled.clearDisplay();
    oled.setTextSize(1);
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(0, 24);
    oled.print(F("Smart Space v3.0"));
    oled.setCursor(0, 36);
    oled.print(F("Connecting WiFi..."));
    oled.display();
    Serial.println("[OLED] OK!");
  }

  Serial.print("[WiFi] ");
  Serial.print(ssid);
  WiFi.begin(ssid, pass);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30)
  {
    delay(500);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED)
  {
    WiFi.setSleep(false);
    Serial.println(" OK!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  }
  else
  {
    Serial.println(" FAIL!");
    return;
  }

  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setKeepAlive(30);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(512);
  connectMqtt();

  // WiFi连上后更新OLED
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setCursor(0, 24);
  oled.print(F("WiFi Connected!"));
  oled.setCursor(0, 36);
  oled.print(WiFi.localIP());
  oled.display();
  delay(2000);

  Serial.println("[System] Ready!");
}

void loop()
{
  if (!mqtt.connected())
  {
    connectMqtt();
  }
  mqtt.loop();
  updateBuzzer();

  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL)
  {
    lastSend = now;
    publishSensors();
  }
}
