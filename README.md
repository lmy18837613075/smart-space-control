# 智能空间控制系统 (Smart Space Control)

基于 **ESP32 + MQTT + FastAPI + Vue-free 前端** 的轻量物联网智能空间控制系统。

## 系统架构

```
ESP32 (传感器/执行器)
    ↕ MQTT (1883)
本地 Broker (amqtt)
    ↕
FastAPI 后端 → SQLite 数据库
    ↕ REST API
前端页面 (index.html)
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 温湿度监测 | DHT11 传感器，2秒采样，实时上报 |
| 光照检测 | 光敏电阻 ADC 采集，百分比换算 |
| 人体感应 | 光遮断传感器（可替换 HC-SR501 PIR） |
| 继电器控制 | 前端开关远程控制，状态双向同步 |
| 蜂鸣器 | 温度报警（>35°C）+ 前端手动蜂鸣测试 |
| OLED 显示 | 0.96寸 SSD1306，实时显示传感器状态 |
| 数据可视化 | Chart.js 绘制 24h 温湿度/光照趋势图 |
| 暗色主题 | 自动跟随时间切换，支持手动锁定 |

## 硬件清单

| 组件 | 引脚 | 备注 |
|------|------|------|
| ESP32 开发板 | - | 推荐 ESP32-WROOM-32 |
| DHT11 温湿度传感器 | GPIO21 | 数字信号 |
| 光敏电阻模块 | GPIO34 (ADC) | 模拟信号 |
| 光遮断传感器 | GPIO32 | 可替换为 HC-SR501 |
| 5V 继电器模块 | GPIO27 | 高电平触发 |
| 有源蜂鸣器 | GPIO25 | 高电平发声 |
| OLED SSD1306 (128x64) | GPIO18(SDA) / GPIO19(SCL) | I2C 地址 0x3C |

## 快速开始

### 1. 硬件端（ESP32）

1. 安装 Arduino IDE 及 ESP32 开发板支持
2. 安装依赖库：
   - `PubSubClient` (MQTT)
   - `DHT sensor library` + `Adafruit Unified Sensor`
   - `Adafruit SSD1306` + `Adafruit GFX`
3. 修改 `firmware/smart_space_control.ino` 中的 WiFi 和 MQTT 配置
4. 编译上传到 ESP32

### 2. 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 终端1：启动 MQTT Broker
python local_broker.py

# 终端2：启动后端服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端

浏览器访问 http://localhost:8000 即可打开控制面板。

## API 接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 系统状态（MQTT连接、运行时间、记录数） |
| `/api/sensors/latest` | GET | 最新一条传感器数据 |
| `/api/sensors/history?hours=24` | GET | 历史数据（默认24小时） |
| `/api/devices/status` | GET | 设备在线状态及继电器状态 |
| `/api/devices/control` | POST | 发送控制指令（继电器开关） |
| `/api/devices/beep` | POST | 蜂鸣器测试 |

## MQTT 主题

| 主题 | 方向 | 内容 |
|------|------|------|
| `esp32/sensors` | ESP32 → Broker | 温湿度/光照/人体感应 JSON |
| `esp32/status` | ESP32 → Broker | 设备在线状态、继电器状态 |
| `esp32/control` | Broker → ESP32 | 控制指令（继电器/蜂鸣器） |

## 项目结构

```
├── firmware/                    # ESP32 固件源码
│   └── smart_space_control.ino
├── app/                         # FastAPI 后端
│   ├── __init__.py
│   ├── main.py                  # 主程序 & API 路由
│   ├── database.py              # SQLite 异步数据库
│   ├── models.py                # Pydantic 数据模型
│   └── mqtt_subscriber.py       # MQTT 订阅与发布
├── frontend/
│   └── index.html               # 前端控制面板（单文件）
├── local_broker.py              # 本地 MQTT Broker 启动脚本
├── requirements.txt             # Python 依赖
└── README.md
```

## 注意事项

- ESP32 固件中的 WiFi 密码和 MQTT 服务器 IP 需根据实际环境修改
- MQTT keepalive 设置为 30 秒，配合 `WiFi.setSleep(false)` 保证连接稳定
- 后端时间戳使用服务器本地时间，不依赖 ESP32 的 millis()
- Windows 环境下 MQTT Broker 使用 ProactorEventLoop 避免兼容性问题

## License

MIT
