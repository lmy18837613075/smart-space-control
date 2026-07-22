import asyncio
import os
import sys

os.system(f"{sys.executable} -m pip install amqtt --quiet 2>nul")

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
    print("监听端口: 1883")
    print("按 Ctrl+C 停止")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await broker.shutdown()

if __name__ == "__main__":
    # 修复Windows asyncio兼容性
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
