#include <WiFi.h>
#include <PubSubClient.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>

// ============ WiFi 配置 ============
const char* ssid = "3546vip.com";
const char* password = "f123456789";

// ============ MQTT 配置 ============
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/control";
const char* client_id = "ESP32_001";

// ============ 硬件引脚定义 ============
#define RELAY1_PIN 12   // 继电器1信号 (GPIO12)
#define IR_RECV_PIN 4   // 红外接收头 OUT (GPIO4)
#define IR_SEND_PIN 5   // 红外发射管 (GPIO5/D13)

// ============ 对象实例 ============
WiFiClient espClient;
PubSubClient mqttClient(espClient);
IRsend irsend(IR_SEND_PIN);

// ============ WiFi 连接 ============
void setupWiFi() {
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// ============ MQTT 回调 ============
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("收到指令: ");

  // relay1_on  → 继电器闭合（低电平触发）
  if (length >= 9 && strncmp((char*)payload, "relay1_on", 9) == 0) {
    digitalWrite(RELAY1_PIN, LOW);
    Serial.println("继电器1 闭合");
    mqttClient.publish("esp32/status", "relay1_on_ok");
  }
  // relay1_off → 继电器断开
  else if (length >= 10 && strncmp((char*)payload, "relay1_off", 10) == 0) {
    digitalWrite(RELAY1_PIN, HIGH);
    Serial.println("继电器1 断开");
    mqttClient.publish("esp32/status", "relay1_off_ok");
  }
  // ir_send → 发射红外信号（rawData 需提前填入）
  else if (length >= 7 && strncmp((char*)payload, "ir_send", 7) == 0) {
    Serial.println("发射红外信号...");
    // TODO: 填入采集的 rawData
    // irsend.sendRaw(rawDataAC, rawDataLEN, 38);
    mqttClient.publish("esp32/status", "ir_sent_ok");
  }
}

// ============ MQTT 重连 ============
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect(client_id)) {
      Serial.println("MQTT connected");
      mqttClient.subscribe(mqtt_topic);
      mqttClient.publish("esp32/status", "online");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// ============ 初始化 ============
void setup() {
  Serial.begin(115200);

  // 初始化硬件
  pinMode(RELAY1_PIN, OUTPUT);
  digitalWrite(RELAY1_PIN, HIGH);  // 继电器默认断开
  irsend.begin();

  // 连接WiFi
  setupWiFi();

  // 设置MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
}

// ============ 主循环 ============
void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
}
