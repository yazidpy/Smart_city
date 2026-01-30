from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import cv2
import json
import numpy as np
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from pipeline import VideoPipeline
from models import (
    init_db,
    list_cameras,
    create_camera,
    get_camera,
    delete_camera,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR= Path(__file__).resolve().parent
VIDEO_DIR = (BASE_DIR / "../Object_detection/video").resolve()
VIDEO_TEST_DIR = (BASE_DIR / "video_test").resolve()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    await init_db()
    # Initialize and start video pipeline
    pipeline = VideoPipeline(
    video_path=str(VIDEO_TEST_DIR / "video.mp4"),
    model_path=str(BASE_DIR / "../Train/detect/train3/weights/best.pt"),
)
    app.state.pipeline = pipeline
    pipeline.start()

    app.state.active_camera_id = None

    async def _broadcast_loop():
        while True:
            try:
                metrics = app.state.pipeline.get_latest_metrics()
                if metrics:
                    await manager.broadcast(metrics)
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
            await asyncio.sleep(0.2)

    app.state.broadcast_task = asyncio.create_task(_broadcast_loop())
    yield
    # Cleanup
    if hasattr(app.state, "pipeline"):
        app.state.pipeline.stop()
    if hasattr(app.state, "broadcast_task"):
        app.state.broadcast_task.cancel()

app = FastAPI(
    title="Smart City Traffic API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (e.g., processed frames)
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; pipeline will broadcast updates
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/video_feed")
def video_feed():
    """MJPEG streaming endpoint for the dashboard."""
    def generate():
        while True:
            frame = app.state.pipeline.get_latest_frame()
            if frame is not None:
                ret, jpeg = cv2.imencode(".jpg", frame,[cv2.IMWRITE_JPEG_QUALITY, 60])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            else:
                # If no frame, send a placeholder
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                ret, jpeg = cv2.imencode(".jpg", placeholder,[cv2.IMWRITE_JPEG_QUALITY, 60])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(1/10)  # ~30 fps
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/videos")
def list_videos():
    if not VIDEO_TEST_DIR.exists():
        return {"videos": []}
    videos = sorted([p.name for p in VIDEO_TEST_DIR.glob("*.mp4")])
    return {"videos": videos}

@app.post("/api/videos/select")
async def select_video(payload: Dict[str, Any]):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
    video_path = (VIDEO_TEST_DIR / name).resolve()
    if not video_path.exists() or video_path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=404, detail="Video not found")
    app.state.pipeline.request_video_source(str(video_path))
    return {"ok": True, "selected": name}


@app.get("/api/cameras")
async def api_list_cameras():
    cams = await list_cameras()
    return {"cameras": cams, "active_camera_id": getattr(app.state, "active_camera_id", None)}


@app.post("/api/cameras")
async def api_create_camera(payload: Dict[str, Any]):
    name = payload.get("name")
    source_url = payload.get("source_url")
    zone_name = payload.get("zone_name")
    roi_polygon = payload.get("roi_polygon")
    if not name or not source_url:
        raise HTTPException(status_code=400, detail="Missing 'name' or 'source_url'")
    if roi_polygon is not None and not isinstance(roi_polygon, list):
        raise HTTPException(status_code=400, detail="Invalid 'roi_polygon' (must be a list of points)")
    cam = await create_camera(name=name, source_url=source_url, zone_name=zone_name, roi_polygon=roi_polygon)
    return cam


@app.delete("/api/cameras/{camera_id}")
async def api_delete_camera(camera_id: int):
    ok = await delete_camera(camera_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Camera not found")
    # If active camera deleted, unset
    if getattr(app.state, "active_camera_id", None) == camera_id:
        app.state.active_camera_id = None
        app.state.pipeline.request_roi(None)
    return {"ok": True}


@app.post("/api/cameras/{camera_id}/select")
async def api_select_camera(camera_id: int):
    cam = await get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    app.state.active_camera_id = camera_id
    # Switch source (can be a local file path or an RTSP/http URL)
    app.state.pipeline.request_video_source(cam["source_url"])
    # Apply camera ROI if any
    app.state.pipeline.request_roi(cam.get("roi_polygon"))
    return {"ok": True, "active_camera_id": camera_id, "camera": cam}

@app.get("/api/metrics/realtime")
async def get_realtime_metrics():
    """Return latest aggregated metrics (current counts, traffic state, risks)."""
    if not hasattr(app.state, "pipeline"):
        raise HTTPException(status_code=503, detail="Pipeline not ready")
    metrics = app.state.pipeline.get_latest_metrics()
    return JSONResponse(metrics)

@app.get("/api/metrics/history")
async def get_metrics_history(
    start: str = None,
    end: str = None,
    granularity: str = "minute"  # minute, hour, day
):
    """Return historical metrics for comparison and reports."""
    # Parse start/end datetime strings (ISO)
    if start:
        start_dt = datetime.fromisoformat(start)
    else:
        start_dt = datetime.now() - timedelta(days=7)
    if end:
        end_dt = datetime.fromisoformat(end)
    else:
        end_dt = datetime.now()
    # Query DB (placeholder for now)
    async with aiosqlite.connect("traffic.db") as db:
        cursor = await db.execute(
            "SELECT * FROM metrics WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
            (start_dt.isoformat(), end_dt.isoformat())
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        history = [dict(zip(columns, row)) for row in rows]
    return JSONResponse(history)
@app.post("/api/reports/generate")
async def generate_report(report_type: str = "daily", date: str = None):
    """Generate a PDF/HTML report for a given day."""
    # Placeholder: generate a simple HTML report using Jinja2
    if not date:
        date = datetime.now().date().isoformat()
    # Fetch data for the date
    async with aiosqlite.connect("traffic.db") as db:
        cursor = await db.execute(
            "SELECT * FROM metrics WHERE DATE(timestamp) = ? ORDER BY timestamp",
            (date,)
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
    # Simple HTML template (you can replace with a proper Jinja2 template)
    html = f"""
    <html><head><title>Traffic Report {date}</title></head><body>
    <h1>Traffic Report for {date}</h1>
    <pre>{json.dumps(data, indent=2)}</pre>
    </body></html>
    """
    return HTMLResponse(content=html)

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
