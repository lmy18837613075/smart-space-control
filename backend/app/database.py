"""
智能空间控制系统 - 数据库模块 v3.0
支持：温度、湿度、亮度、人体感应
"""

import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "data/smart_space.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                light INTEGER DEFAULT 0,
                motion INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_time
            ON sensor_readings(device_id, timestamp)
        """)
        await db.commit()


async def save_sensor_reading(device_id, temperature, humidity,
                              light=0, motion=0, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sensor_readings
               (device_id, temperature, humidity, light, motion, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (device_id, temperature, humidity, light, motion, str(timestamp))
        )
        await db.commit()


async def get_latest_reading(device_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if device_id:
            cursor = await db.execute(
                """SELECT * FROM sensor_readings
                   WHERE device_id = ?
                   ORDER BY timestamp DESC LIMIT 1""",
                (device_id,)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM sensor_readings
                   ORDER BY timestamp DESC LIMIT 1"""
            )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def get_sensor_history(hours=24, device_id=None):
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if device_id:
            cursor = await db.execute(
                """SELECT * FROM sensor_readings
                   WHERE device_id = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (device_id, cutoff)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM sensor_readings
                   WHERE timestamp >= ?
                   ORDER BY timestamp ASC""",
                (cutoff,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_sensor_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM sensor_readings")
        row = await cursor.fetchone()
        return row[0] if row else 0
