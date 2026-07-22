"""
智能空间控制系统 - 后端主程序 v3.0
FastAPI 应用，提供：
  - REST API（传感器数据、设备控制）
  - 静态文件服务（前端页面）
  - MQTT 通信
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from . import database
from . import mqtt_subscriber
from .models import StatusResponse, DeviceCommand


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    mqtt_subscriber.start_mqtt()
    print("\n" + "=" * 50)
    print("  智能空间控制系统 v3.0")
    print("  前端页面: http://localhost:8000")
    print("  API 接口: http://localhost:8000/api")
    print("=" * 50 + "\n")
    yield
    mqtt_subscriber.stop_mqtt()


app = FastAPI(
    title="智能空间控制系统",
    description="ESP32 + MQTT + FastAPI 物联网系统",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== API =====

@app.get("/api")
async def root():
    return {
        "name": "智能空间控制系统 API",
        "version": "3.0.0",
        "endpoints": {
            "/api/status": "系统状态",
            "/api/sensors/latest": "最新传感器数据",
            "/api/sensors/history": "历史数据",
            "/api/devices/status": "设备状态",
            "/api/devices/control": "发送控制指令 (POST)",
            "/api/devices/beep": "测试蜂鸣器 (POST)"
        }
    }


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    uptime = (datetime.now() - mqtt_subscriber.start_time).total_seconds()
    h = int(uptime // 3600)
    m = int((uptime % 3600) // 60)
    count = await database.get_sensor_count()
    return StatusResponse(
        status="running",
        mqtt_connected=mqtt_subscriber.mqtt_connected,
        sensor_count=count,
        uptime=f"{h}h {m}m"
    )


@app.get("/api/sensors/latest")
async def get_latest(device_id: str = None):
    reading = await database.get_latest_reading(device_id)
    if reading:
        return {"status": "ok", "data": reading}
    return {"status": "ok", "data": None, "message": "暂无数据"}


@app.get("/api/sensors/history")
async def get_history(hours: int = Query(default=24, ge=1, le=720), device_id: str = None):
    readings = await database.get_sensor_history(hours, device_id)
    return {"status": "ok", "count": len(readings), "data": readings}


@app.get("/api/devices/status")
async def get_device_status():
    state = mqtt_subscriber.get_device_state()
    return {"status": "ok", "data": state}


@app.post("/api/devices/control")
async def control_device(cmd: DeviceCommand):
    success = mqtt_subscriber.publish_command({
        "device_id": cmd.device_id,
        "command": cmd.command,
        "channel": cmd.channel
    })
    if success:
        return {"status": "ok", "message": f"已发送: {cmd.command}"}
    return {"status": "error", "message": "MQTT 未连接"}


@app.post("/api/devices/beep")
async def beep_device():
    success = mqtt_subscriber.publish_command({
        "device_id": "esp32_001",
        "beep": "test"
    })
    if success:
        return {"status": "ok", "message": "蜂鸣测试已发送"}
    return {"status": "error", "message": "MQTT 未连接"}


# ===== Frontend =====

FRONTEND_DIR = Path(__file__).parent.parent

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "智能空间控制系统 API 运行中!"}


@app.get("/favicon.ico")
async def favicon():
    return {"status": "ok"}
