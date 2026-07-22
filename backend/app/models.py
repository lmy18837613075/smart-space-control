"""
智能空间控制系统 - 数据模型 v3.0
"""

from pydantic import BaseModel
from typing import Optional


class StatusResponse(BaseModel):
    status: str
    mqtt_connected: bool
    sensor_count: int
    uptime: str


class DeviceCommand(BaseModel):
    device_id: str = "esp32_001"
    command: str
    channel: int = 1
