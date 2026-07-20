"""
本地 MQTT Broker - 基于 amqtt
运行: python local_broker.py
监听 0.0.0.0:1883，允许匿名连接
"""
import asyncio
from amqtt.broker import Broker

config = {
    "listeners": {
        "default": {
            "type": "tcp",
            "bind": "0.0.0.0:1883",
        }
    },
    "sys_interval": 0,
    "auth": {"allow-anonymous": True},
    "topic-check": {"enabled": False},
}

async def main():
    broker = Broker(config)
    await broker.start()
    print("=== 本地 MQTT Broker 已启动 ===")
    print("端口: 1883 | 等待 ESP32 连接...\n")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n停止中...")
        await broker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
