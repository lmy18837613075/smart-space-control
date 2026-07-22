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
    print("  Smart Space Control v3.0")
    print("  Frontend: http://localhost:8000")
    print("  API:      http://localhost:8000/api")
    print("=" * 50 + "\n")
    yield
    mqtt_subscriber.stop_mqtt()


app = FastAPI(
    title="Smart Space Control",
    description="ESP32 + MQTT + FastAPI IoT System",
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
        "name": "Smart Space Control API",
        "version": "3.0.0",
        "endpoints": {
            "/api/status": "System status",
            "/api/sensors/latest": "Latest sensor data",
            "/api/sensors/history": "Historical data",
            "/api/devices/status": "Device state",
            "/api/devices/control": "Send control command (POST)",
            "/api/devices/beep": "Test buzzer (POST)"
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
    return {"status": "ok", "data": None, "message": "No data yet"}


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
        return {"status": "ok", "message": f"Sent: {cmd.command}"}
    return {"status": "error", "message": "MQTT not connected"}


@app.post("/api/devices/beep")
async def beep_device():
    """测试蜂鸣器"""
    success = mqtt_subscriber.publish_command({
        "device_id": "esp32_001",
        "beep": "test"
    })
    if success:
        return {"status": "ok", "message": "Beep sent"}
    return {"status": "error", "message": "MQTT not connected"}


# ===== 前端服务 =====

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Smart Space Control API is running!"}


@app.get("/favicon.ico")
async def favicon():
    return {"status": "ok"}
