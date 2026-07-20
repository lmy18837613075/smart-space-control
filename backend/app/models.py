"""
智能空间控制系统 - 数据模型（Pydantic）
定义 API 的请求体和响应体结构，FastAPI 自动校验和序列化
"""

from pydantic import BaseModel
from typing import Optional


class SensorReading(BaseModel):
    """传感器读数"""
    device_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: Optional[str] = None


class DeviceCommand(BaseModel):
    """设备控制指令: {"device_id":"esp32_001", "command":"on/off", "channel":1}"""
    device_id: str
    command: str                      # on 或 off
    channel: Optional[int] = 1        # 继电器通道，预留多路


class StatusResponse(BaseModel):
    """系统状态响应"""
    status: str                       # running
    mqtt_connected: bool              # MQTT 是否连接
    sensor_count: int                 # 数据总条数
    uptime: str                       # 运行时长，如 "2h 30m"
