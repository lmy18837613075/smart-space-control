"""
智能空间控制系统 - MQTT 通信模块
负责：
  1. 连接本地 MQTT Broker
  2. 订阅 esp32/sensors 主题，接收温湿度数据并存入数据库
  3. 订阅 esp32/status 主题，接收设备实际状态（闭环反馈）
  4. 向 esp32/control 主题发布控制指令
"""

import paho.mqtt.client as mqtt
import json
import asyncio
from datetime import datetime
from . import database

# MQTT Broker 配置
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
CLIENT_ID = "smartspace_backend"

# 主题定义
TOPIC_SENSORS = "esp32/sensors"    # ESP32 → 后端：温湿度数据
TOPIC_CONTROL = "esp32/control"    # 后端 → ESP32：控制指令
TOPIC_STATUS  = "esp32/status"     # ESP32 → 后端：设备实际状态反馈

# 全局状态
mqtt_connected = False
start_time = datetime.now()
mqtt_client = None

# 设备实际状态（由 ESP32 上报更新，闭环反馈的核心）
device_state = {
    "relay": False,       # 继电器实际开关状态
    "online": False,      # 设备是否在线
    "last_update": None   # 最后一次状态上报时间
}


def on_connect(client, userdata, flags, reason_code, properties=None):
    """MQTT 连接成功回调：订阅传感器和状态主题"""
    global mqtt_connected
    if reason_code == 0:
        mqtt_connected = True
        print(f"[MQTT] Connected!")
        client.subscribe(TOPIC_SENSORS)
        client.subscribe(TOPIC_STATUS)  # 订阅设备状态反馈
        print(f"[MQTT] Subscribed to {TOPIC_SENSORS}, {TOPIC_STATUS}")
    else:
        mqtt_connected = False
        print(f"[MQTT] Failed, rc={reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    """MQTT 断开回调"""
    global mqtt_connected
    mqtt_connected = False
    print(f"[MQTT] Disconnected, rc={reason_code}")


def on_message(client, userdata, msg):
    """收到 MQTT 消息回调"""
    topic = msg.topic
    payload = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] {topic}: {payload}")

    if topic == TOPIC_SENSORS:
        try:
            data = json.loads(payload)
            device_id = data.get("device_id", "esp32_001")
            temperature = data.get("temperature") or data.get("temp")
            humidity = data.get("humidity") or data.get("hum")
            ts = data.get("timestamp") or data.get("ts", "")
            timestamp = str(ts) if ts else datetime.now().isoformat()

            # 传感器数据中也包含 relay 状态，同步更新
            if "relay" in data:
                device_state["relay"] = data["relay"]
                device_state["online"] = True
                device_state["last_update"] = datetime.now().isoformat()

            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                database.save_sensor_reading(device_id, temperature, humidity, timestamp)
            )
            loop.close()
            print(f"[DB] Saved: {device_id} {temperature}C {humidity}%")
        except Exception as e:
            print(f"[ERROR] {e}")

    elif topic == TOPIC_STATUS:
        # 设备状态反馈（ESP32 执行控制指令后上报）
        try:
            data = json.loads(payload)
            device_state["relay"] = data.get("relay", False)
            device_state["online"] = data.get("online", True)
            device_state["last_update"] = datetime.now().isoformat()
            print(f"[Status] relay={'ON' if device_state['relay'] else 'OFF'} online={device_state['online']}")
        except Exception as e:
            print(f"[Status ERROR] {e}")


def get_device_state():
    """获取设备当前实际状态（供 API 调用）"""
    return device_state.copy()


def publish_command(command):
    """发布控制指令到 ESP32"""
    if not mqtt_connected or not mqtt_client:
        return False
    try:
        payload = json.dumps(command)
        mqtt_client.publish(TOPIC_CONTROL, payload)
        print(f"[MQTT] Published: {payload}")
        return True
    except Exception as e:
        print(f"[MQTT] Publish failed: {e}")
        return False


def start_mqtt():
    """启动 MQTT 客户端，连接 Broker 并开始收发消息"""
    global mqtt_client
    mqtt_client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.reconnect_delay_set(min_delay=5, max_delay=30)
    try:
        mqtt_client.connect(BROKER_HOST, BROKER_PORT, 60)
        mqtt_client.loop_start()
        print("[MQTT] Started")
    except Exception as e:
        print(f"[MQTT] Connect failed: {e}")


def stop_mqtt():
    """停止 MQTT 客户端"""
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
