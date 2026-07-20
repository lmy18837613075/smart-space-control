"""
智能空间控制系统 - 数据库模块
使用 aiosqlite 异步操作 SQLite，数据库文件: backend/data/smartspace.db
"""

import aiosqlite
import os

# 数据库路径
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "smartspace.db"))


async def init_db():
    """初始化数据库表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_time
            ON sensor_data(device_id, timestamp)
        """)
        await db.commit()


async def save_sensor_reading(device_id, temperature, humidity, timestamp):
    """保存一条传感器数据"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sensor_data (device_id, temperature, humidity, timestamp) VALUES (?, ?, ?, ?)",
            (device_id, temperature, humidity, timestamp)
        )
        await db.commit()


async def get_latest_reading(device_id=None):
    """获取最新一条数据，device_id 为空则取全局最新"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if device_id:
            cursor = await db.execute(
                "SELECT * FROM sensor_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1",
                (device_id,)
            )
        else:
            cursor = await db.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_sensor_history(hours=24, device_id=None):
    """获取最近 N 小时的历史数据，按时间升序"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM sensor_data WHERE timestamp >= datetime('now', ?)"
        params = [f"-{hours} hours"]
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        query += " ORDER BY timestamp ASC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_sensor_count():
    """获取数据总条数"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM sensor_data")
        row = await cursor.fetchone()
        return row[0] if row else 0
