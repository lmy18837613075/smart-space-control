/*
  智能空间控制系统 - ESP32 固件
  功能：读取 DHT11 温湿度 → MQTT 上报；接收 MQTT 指令 → 控制继电器 → 上报实际状态

  接线：
    DHT11 DATA → GPIO21
    继电器 IN  → GPIO27
    继电器 VCC → VIN (5V)

  MQTT 主题：
    发布 esp32/sensors  → {"device_id":"xxx","temp":25.0,"hum":60.0,"relay":false,"ts":12345}
    发布 esp32/status   → {"device_id":"xxx","relay":true,"online":true,"ts":12345}
    订阅 esp32/control  → {"command":"on/off","channel":1}
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// === WiFi 配置（上传前请修改） ===
const char* ssid = "YOUR_WIFI_SSID";
const char* pass = "YOUR_WIFI_PASSWORD";

// === MQTT 配置（填 Broker 所在机器的局域网 IP） ===
const char* mqtt_server = "YOUR_BROKER_IP";
const int mqtt_port = 1883;
char mqtt_client_id[32];

// === 主题 ===
const char* topic_sensors = "esp32/sensors";
const char* topic_control = "esp32/control";
const char* topic_status  = "esp32/status";   // 状态反馈

// === GPIO ===
#define DHT_PIN    21
#define DHT_TYPE   DHT11
#define RELAY_PIN  27

// === 全局对象 ===
WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(DHT_PIN, DHT_TYPE);

// === 状态 ===
unsigned long lastSend = 0;
const unsigned long SEND_INTERVAL = 5000; // 传感器上报间隔 5 秒
bool relayState = false;                   // 继电器当前实际状态

// 发布设备状态到 esp32/status
void publishStatus() {
  char payload[128];
  snprintf(payload, sizeof(payload),
    "{\"device_id\":\"%s\",\"relay\":%s,\"online\":true,\"ts\":%lu}",
    mqtt_client_id, relayState ? "true" : "false", millis());
  mqtt.publish(topic_status, payload);
  Serial.print("[Status] relay=");
  Serial.println(relayState ? "ON" : "OFF");
}

// 收到控制指令回调
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  char buf[256];
  unsigned int len = length < sizeof(buf) - 1 ? length : sizeof(buf) - 1;
  memcpy(buf, payload, len);
  buf[len] = '\0';

  Serial.print("[MQTT] 收到: ");
  Serial.println(buf);

  // 提取 command 字段
  String msg = String(buf);
  int cmdStart = msg.indexOf("\"command\"");
  if (cmdStart == -1) return;
  cmdStart = msg.indexOf(":", cmdStart);
  if (cmdStart == -1) return;
  int valStart = msg.indexOf("\"", cmdStart);
  if (valStart == -1) return;
  int valEnd = msg.indexOf("\"", valStart + 1);
  if (valEnd == -1) return;
  String cmd = msg.substring(valStart + 1, valEnd);

  // 执行继电器动作
  if (cmd == "on") {
    digitalWrite(RELAY_PIN, HIGH);
    relayState = true;
    Serial.println("[Relay] ON");
  } else if (cmd == "off") {
    digitalWrite(RELAY_PIN, LOW);
    relayState = false;
    Serial.println("[Relay] OFF");
  }

  // 立即上报实际状态（闭环反馈）
  publishStatus();
}

// 连接 MQTT（断线自动重连）
void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("[MQTT] 连接中...");
    if (mqtt.connect(mqtt_client_id)) {
      Serial.println(" OK!");
      mqtt.subscribe(topic_control);
      // 上线即上报初始状态
      publishStatus();
    } else {
      Serial.print(" 失败, rc=");
      Serial.println(mqtt.state());
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  // 用 MAC 地址后 4 位作为唯一 Client ID
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(mqtt_client_id, sizeof(mqtt_client_id), "ESP32_%02X%02X%02X%02X", mac[2], mac[3], mac[4], mac[5]);

  Serial.println("\n=== Smart Space Control ===");
  Serial.print("Client ID: ");
  Serial.println(mqtt_client_id);

  dht.begin();

  // 连接 WiFi
  Serial.print("[WiFi] 连接 ");
  Serial.print(ssid);
  WiFi.begin(ssid, pass);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" OK!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" 失败!");
    return;
  }

  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(512);
  connectMqtt();

  Serial.println("[System] 就绪!");
}

void loop() {
  if (!mqtt.connected()) {
    connectMqtt();
  }
  mqtt.loop();

  // 定时上报传感器数据（顺带 relay 状态）
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL) {
    lastSend = now;

    float t = dht.readTemperature();
    float h = dht.readHumidity();

    if (!isnan(t) && !isnan(h)) {
      char payload[128];
      snprintf(payload, sizeof(payload),
        "{\"device_id\":\"%s\",\"temp\":%.1f,\"hum\":%.1f,\"relay\":%s,\"ts\":%lu}",
        mqtt_client_id, t, h, relayState ? "true" : "false", now);

      mqtt.publish(topic_sensors, payload);
      Serial.print("[传感器] ");
      Serial.print(t);
      Serial.print("°C  ");
      Serial.print(h);
      Serial.print("%  relay=");
      Serial.println(relayState ? "ON" : "OFF");
    } else {
      Serial.println("[传感器] 读取失败!");
    }
  }
}
