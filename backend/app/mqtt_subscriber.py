"""
智能空间控制系统 - MQTT 通信模块 v3.0
支持：温湿度、亮度、人体感应、继电器控制、蜂鸣器
"""

import paho.mqtt.client as mqtt
import json
import asyncio
from datetime import datetime
from . import database

# MQTT Broker
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
CLIENT_ID = "smartspace_backend"

# 主题
TOPIC_SENSORS = "esp32/sensors"
TOPIC_CONTROL = "esp32/control"
TOPIC_STATUS  = "esp32/status"

# 全局状态
mqtt_connected = False
start_time = datetime.now()
mqtt_client = None

# 设备状态
device_state = {
    "relay": False,
    "online": False,
    "motion": False,
    "light": 0,
    "last_update": None
}


def on_connect(client, userdata, flags, reason_code, properties=None):
    global mqtt_connected
    if reason_code == 0:
        mqtt_connected = True
        print("[MQTT] Connected!")
        client.subscribe(TOPIC_SENSORS)
        client.subscribe(TOPIC_STATUS)
    else:
        mqtt_connected = False
        print(f"[MQTT] Failed, rc={reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    global mqtt_connected
    mqtt_connected = False
    print("[MQTT] Disconnected")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] {topic}: {payload}")

    if topic == TOPIC_SENSORS:
        try:
            data = json.loads(payload)
            device_id = data.get("device_id", "esp32_001")
            temperature = data.get("temperature") or data.get("temp")
            humidity = data.get("humidity") or data.get("hum")
            light = data.get("light", 0)
            motion = data.get("motion", False)
            ts = data.get("timestamp") or data.get("ts", "")
            # ESP32 millis()不是真实时间，用服务器时间
            timestamp = datetime.now().isoformat()

            if "relay" in data:
                device_state["relay"] = data["relay"]
            device_state["online"] = True
            device_state["motion"] = motion
            device_state["light"] = light
            device_state["last_update"] = datetime.now().isoformat()

            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                database.save_sensor_reading(
                    device_id, temperature, humidity,
                    light, int(motion), timestamp
                )
            )
            loop.close()
            print(f"[DB] Saved: {temperature}C {humidity}% light={light} motion={motion}")
        except Exception as e:
            print(f"[ERROR] {e}")

    elif topic == TOPIC_STATUS:
        try:
            data = json.loads(payload)
            device_state["relay"] = data.get("relay", False)
            device_state["online"] = data.get("online", True)
            device_state["last_update"] = datetime.now().isoformat()
            print(f"[Status] relay={'ON' if device_state['relay'] else 'OFF'}")
        except Exception as e:
            print(f"[Status ERROR] {e}")


def get_device_state():
    return device_state.copy()


def publish_command(command):
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
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
