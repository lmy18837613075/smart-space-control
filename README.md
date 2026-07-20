---
AIGC:
    Label: "1"
    ContentProducer: 001191110102MACQD9K64018705
    ProduceID: 3112094242706266_0/project_7652161027991339304-files/smart-space-control/README_enhanced.md
    ReservedCode1: ""
    ContentPropagator: 001191110102MACQD9K64028705
    PropagateID: 3112094242706266#1784548007868
    ReservedCode2: ""
---
<div align="center">

# 🏠 Smart Space Control

**基于 ESP32 + MQTT + FastAPI 的开源智能空间控制系统**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESP32](https://img.shields.io/badge/ESP32-Arduino-blue.svg)](https://docs.espressif.com/projects/arduino-esp32/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![MQTT](https://img.shields.io/badge/MQTT-3.1.1-orange.svg)](http://mqtt.org/)

**让宿舍/房间变智能，成本不到 100 块！**

[快速开始](#快速开始) • [系统架构](#系统架构) • [功能特性](#功能特性) • [硬件清单](#硬件清单)

</div>

---

## ✨ 为什么选择这个项目？

| 痛点 | 这个项目的解决方案 |
|------|-------------------|
| 商业智能设备太贵 | 💰 总成本 < ¥100，DIY 更省钱 |
| 闭源系统不透明 | 🔓 100% 开源，代码可控 |
| 功能受限难扩展 | 🔧 模块化设计，想加什么加什么 |
| 学习门槛高 | 📚 详细文档 + 完整注释，新手友好 |

## 🎯 功能特性

- 🌡️ **实时监控** - 温湿度数据自动采集，历史曲线可视化
- 💡 **远程控制** - 手机/电脑一键控制继电器（开灯/关风扇）
- 📊 **数据可视化** - Chart.js 动态图表，数据一目了然
- 🔔 **状态推送** - MQTT 实时推送，设备离线自动告警
- 🎨 **OLED 显示** - 双色 OLED 屏幕显示状态 + 像素动画

## 📸 效果展示

> TODO: 添加系统运行截图/GIF

## 🏗️ 系统架构

```
┌─────────────┐     MQTT      ┌──────────────┐     HTTP      ┌─────────────┐
│             │ ─────────────► │              │ ─────────────► │             │
│   ESP32     │   esp32/       │   FastAPI    │                │   前端面板   │
│  + DHT11    │   sensors      │   Backend    │ ◄───────────── │  (HTML/JS)  │
│  + OLED     │ ◄───────────── │  + SQLite    │   /api/*       │             │
│  + Relay    │   esp32/       │              │                │             │
│             │   control      │              │                │             │
└─────────────┘ ─────────────► └──────────────┘                └─────────────┘
       ▲                               │
       │                               ▼
  物理设备控制                      数据存储层
  (灯/风扇等)                     (SQLite DB)
```

## 🛒 硬件清单

| 组件 | 型号/规格 | 参考价格 | 购买链接 |
|------|-----------|----------|----------|
| 主控板 | ESP32 Dev Module | ¥15-25 | 淘宝/拼多多 |
| 温湿度传感器 | DHT11 | ¥3-5 | 淘宝 |
| 继电器模块 | 5V 单路继电器 | ¥3-5 | 淘宝 |
| OLED 屏幕 | 0.96" SSD1306 双色 | ¥10-15 | 淘宝 |
| 杜邦线 | 母对母 若干 | ¥2 | 淘宝 |
| **总计** | - | **< ¥50** | - |

## 🔌 接线图

```
ESP32                    传感器/模块
─────                    ──────────
GPIO21 ───────────────── DHT11 DATA
GPIO27 ───────────────── 继电器 IN
GPIO18 ───────────────── OLED SDA
GPIO19 ───────────────── OLED SCL
3.3V   ───────────────── DHT11 VCC / OLED VCC
VIN    ───────────────── 继电器 VCC
GND    ───────────────── 所有 GND
```

> ⚠️ **注意**: GPIO27 不是 strapping pin，可安全连接继电器。避免使用 GPIO12 等 strapping pin。

## 🚀 快速开始

### 1. 安装后端依赖
```bash
cd smart-space-control/backend
pip install -r requirements.txt
```

### 2. 启动 MQTT Broker
```bash
python local_broker.py
```

### 3. 启动后端服务
```bash
cd smart-space-control/backend
python -m uvicorn app.main:app --reload
```

### 4. 烧录 ESP32 固件
用 Arduino IDE 打开 `esp32_firmware/smart_space_control.ino`，修改配置：
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* pass = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "YOUR_BROKER_IP";
```

### 5. 打开控制面板
浏览器访问 `http://localhost:8000` 🎉

## 📡 MQTT 主题

| 主题 | 方向 | 数据格式 |
|------|------|----------|
| `esp32/sensors` | ESP32 → Broker | `{"device_id":"esp32_01","temp":25.0,"hum":31.0,"ts":...}` |
| `esp32/control` | Broker → ESP32 | `{"device_id":"esp32_01","command":"on/off","channel":1}` |
| `esp32/status` | ESP32 → Broker | `{"device_id":"esp32_01","relay":true,"online":true,"ts":...}` |

## 🔧 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 系统状态 |
| GET | `/api/sensors/latest` | 最新传感器数据 |
| GET | `/api/sensors/history?hours=24` | 历史数据（默认24小时） |
| POST | `/api/devices/control` | 设备控制（开/关） |

## ⚠️ 常见问题

<details>
<summary>ESP32 连不上 WiFi？</summary>

- 只支持 **2.4GHz**，不支持 5GHz
- 检查密码是否正确
- 尝试靠近路由器
</details>

<details>
<summary>继电器不动作？</summary>

- 确认 VCC 接的是 VIN(5V)，不是 3.3V
- 检查 GPIO27 接线是否正确
- 用万用表测量继电器供电
</details>

<details>
<summary>手机热点为什么不行？</summary>

手机热点通常有 **AP 隔离**，设备间无法互相通信。解决方案：
1. 使用普通路由器
2. 用 ESP32 自建 AP 模式（代码已支持）
3. 买个便携路由器（推荐）
</details>

## 📚 技术栈

- **固件**: Arduino C++ (PubSubClient + DHT + Adafruit_SSD1306)
- **Broker**: amqtt (纯 Python MQTT 实现)
- **后端**: FastAPI + aiosqlite + paho-mqtt
- **前端**: 原生 HTML/JS + Chart.js

## 🤝 贡献

欢迎提 Issue 和 PR！

如果觉得有用，请给个 ⭐ Star 支持一下！

## 📄 License

MIT License - 随便用，记得注明出处就行~

---

<div align="center">

**如果这个项目帮到你了，请给作者一个 ⭐ Star 吧！**

Made with ❤️ by [googaga](https://github.com/lmy18837613075)

</div>

---

> 本内容由 Coze AI 生成，请遵循相关法律法规及《人工智能生成合成内容标识办法》使用与传播。
