import aiosqlite
import json
from datetime import datetime
from typing import Dict, Any

DB_PATH = "traffic.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                counts TEXT NOT NULL,
                traffic_state TEXT NOT NULL,
                risk_count INTEGER NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                zone_name TEXT,
                roi_polygon TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp);
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_cameras_name ON cameras(name);
        """)

        try:
            await db.execute("ALTER TABLE cameras ADD COLUMN zone_name TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE cameras ADD COLUMN roi_polygon TEXT")
        except Exception:
            pass
        await db.commit()

async def save_metrics(timestamp: str, counts: Dict[str, int], traffic_state: str, risk_count: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO metrics (timestamp, counts, traffic_state, risk_count) VALUES (?, ?, ?, ?)",
            (timestamp, json.dumps(counts), traffic_state, risk_count)
        )
        await db.commit()


async def list_cameras() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, name, source_url, zone_name, roi_polygon, created_at FROM cameras ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
    out = []
    for r in rows:
        roi_polygon = None
        if r[4]:
            try:
                roi_polygon = json.loads(r[4])
            except Exception:
                roi_polygon = None
        out.append(
            {
                "id": r[0],
                "name": r[1],
                "source_url": r[2],
                "zone_name": r[3],
                "roi_polygon": roi_polygon,
                "created_at": r[5],
            }
        )
    return out


async def create_camera(name: str, source_url: str, zone_name: str | None = None, roi_polygon: list | None = None) -> dict:
    now = datetime.utcnow().isoformat()
    roi_json = json.dumps(roi_polygon) if roi_polygon else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO cameras (name, source_url, zone_name, roi_polygon, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, source_url, zone_name, roi_json, now),
        )
        await db.commit()
        camera_id = cursor.lastrowid
    return {
        "id": camera_id,
        "name": name,
        "source_url": source_url,
        "zone_name": zone_name,
        "roi_polygon": roi_polygon,
        "created_at": now,
    }


async def get_camera(camera_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, name, source_url, zone_name, roi_polygon, created_at FROM cameras WHERE id = ?",
            (camera_id,),
        )
        row = await cursor.fetchone()
    if not row:
        return None
    roi_polygon = None
    if row[4]:
        try:
            roi_polygon = json.loads(row[4])
        except Exception:
            roi_polygon = None
    return {
        "id": row[0],
        "name": row[1],
        "source_url": row[2],
        "zone_name": row[3],
        "roi_polygon": roi_polygon,
        "created_at": row[5],
    }


async def delete_camera(camera_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        await db.commit()
    return cursor.rowcount > 0
