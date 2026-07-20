"""
智能空间控制系统 - 后端主程序 v2.0
FastAPI 应用，提供：
  - REST API（传感器数据、设备控制）
  - 静态文件服务（前端页面）
  - MQTT 通信
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import os

from . import database
from . import mqtt_subscriber
from .models import StatusResponse, DeviceCommand


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和 MQTT，关闭时断开"""
    await database.init_db()
    mqtt_subscriber.start_mqtt()
    print("\n" + "="*50)
    print("  🏠 智能空间控制系统 v2.0")
    print("  📡 前端面板: http://localhost:8000")
    print("  📡 控制 API: http://localhost:8000/api")
    print("="*50 + "\n")
    yield
    mqtt_subscriber.stop_mqtt()


app = FastAPI(
    title="Smart Space Control",
    description="基于 ESP32 + MQTT 的物联网智能空间控制系统",
    version="2.0.0",
    lifespan=lifespan
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== API 路由 =====

@app.get("/api")
async def root():
    """API 根路径"""
    return {
        "name": "Smart Space Control API",
        "version": "2.0.0",
        "endpoints": {
            "/api/status": "系统状态",
            "/api/sensors/latest": "最新传感器数据",
            "/api/sensors/history": "历史数据",
            "/api/devices/status": "设备实际状态",
            "/api/devices/control": "发送控制指令 (POST)"
        }
    }


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """返回系统运行状态"""
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
    """获取最新传感器数据"""
    reading = await database.get_latest_reading(device_id)
    if reading:
        return {"status": "ok", "data": reading}
    return {"status": "ok", "data": None, "message": "No data yet"}


@app.get("/api/sensors/history")
async def get_history(hours: int = Query(default=24, ge=1, le=720), device_id: str = None):
    """获取历史数据，hours 范围 1~720"""
    readings = await database.get_sensor_history(hours, device_id)
    return {"status": "ok", "count": len(readings), "data": readings}


@app.get("/api/devices/status")
async def get_device_status():
    """获取设备实际状态（继电器开关、是否在线）"""
    state = mqtt_subscriber.get_device_state()
    return {"status": "ok", "data": state}


@app.post("/api/devices/control")
async def control_device(cmd: DeviceCommand):
    """通过 MQTT 向 ESP32 发送控制指令"""
    success = mqtt_subscriber.publish_command({
        "device_id": cmd.device_id,
        "command": cmd.command,
        "channel": cmd.channel
    })
    if success:
        return {"status": "ok", "message": f"Sent: {cmd.command} to {cmd.device_id}"}
    return {"status": "error", "message": "MQTT not connected"}


# ===== 静态文件服务（前端页面）=====

# 前端文件目录
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

@app.get("/")
async def serve_index():
    """提供前端主页"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Smart Space Control API is running!", "note": "Frontend not found"}


@app.get("/favicon.ico")
async def favicon():
    """返回空响应避免 404"""
    return {"status": "ok"}
