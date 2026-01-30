import cv2
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from collections import defaultdict, deque
from pathlib import Path
import threading

from ultralytics import YOLO
from tracking import ByteTracker
from utils import compute_traffic_state
from models import save_metrics

logger = logging.getLogger(__name__)

class VideoPipeline:
    def __init__(self, video_path: str, model_path: str):
        self.video_path = video_path
        self.model_path = model_path
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(video_path)
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.running = False
        self.latest_frame = None
        self.latest_metrics = {}
        self._lock = threading.Lock()
        self._cap_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._pending_video_path: Optional[str] = None
        self._roi_lock = threading.Lock()
        self._roi_polygon: Optional[list] = None
        self._is_live_source = False
        self.tracker = ByteTracker()
        self.frame_count = 0
        self.last_save_time = datetime.utcnow()
        # Aggregation windows
        self.per_minute_counts = defaultdict(lambda: defaultdict(int))
        self.current_minute = None
        # Classes
        self.classes = {
            0: "Person",
            1: "Bicycle",
            2: "Car",
            3: "Motorcycle",
            4: "Bus",
            5: "Truck"
        }
        self.colors = {
            "Person": (0, 255, 0),
            "Car": (255, 0, 0),
            "Bus": (0, 165, 255),
            "Truck": (0, 0, 255),
            "Motorcycle": (255, 255, 0),
            "Bicycle": (255, 0, 255)
        }

    def start(self):
        """Start the pipeline in a dedicated background thread."""
        if self._thread and self._thread.is_alive():
            return
        self.running = True

        def _runner():
            try:
                asyncio.run(self.run())
            except Exception as e:
                logger.exception(f"Pipeline thread crashed: {e}")

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()

    async def run(self):
        logger.info(f"Starting pipeline for {self.video_path}")
        while self.running:
            pending = None
            with self._cap_lock:
                if self._pending_video_path:
                    pending = self._pending_video_path
                    self._pending_video_path = None
            if pending:
                self._switch_video_source(pending)

            with self._cap_lock:
                if self._is_live_source and self.cap is not None:
                    try:
                        for _ in range(2):
                            self.cap.grab()
                    except Exception:
                        pass
                ret, frame = self.cap.read()
            if not ret:
                # Loop video or stop
                with self._cap_lock:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            self.frame_count += 1
            if self.frame_count % 2 != 0:
                continue

            now = datetime.utcnow()
            # Resize for faster inference (optional)
            if self._is_live_source:
                frame = cv2.resize(frame, (640, 360))
            else:
                frame = cv2.resize(frame, (960, 540))
            # Inference
            results = self.model(frame, conf=0.35, iou=0.5, verbose=False)
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append({
                        "cls": cls_id,
                        "conf": conf,
                        "bbox": [float(x1), float(y1), float(x2), float(y2)]
                    })

            # Apply ROI filtering (if configured)
            with self._roi_lock:
                roi = self._roi_polygon
            if roi:
                detections = [d for d in detections if self._is_detection_in_roi(d, roi)]
            # Tracking
            tracked_objects = self.tracker.update(detections)
            ts = now.isoformat()
            for obj in tracked_objects:
                obj["timestamp"] = ts
            # Count unique objects per class (by track_id)
            current_counts = defaultdict(int)
            for obj in tracked_objects:
                cls_name = self.classes.get(obj["cls"], "unknown")
                current_counts[cls_name] += 1
                # Draw
                x1, y1, x2, y2 = obj["bbox"]
                color = self.colors.get(cls_name, (200, 200, 200))
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                label = f"{cls_name} {obj['conf']:.2f} ID:{obj['track_id']}"
                cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            # Compute traffic state
            traffic_state = compute_traffic_state(current_counts)
            # Update per-minute aggregation
            minute_key = now.replace(second=0, microsecond=0)
            for cls, cnt in current_counts.items():
                self.per_minute_counts[minute_key][cls] += cnt
            # Prepare metrics
            metrics = {
                "timestamp": now.isoformat(),
                "frame": self.frame_count,
                "counts": dict(current_counts),
                "traffic_state": traffic_state,
                "fps": self.fps
            }
            with self._lock:
                self.latest_metrics = metrics
                self.latest_frame = frame.copy()
            # Save aggregated metrics every minute
            if now - self.last_save_time >= timedelta(minutes=1):
                await self._save_minute_metrics(minute_key)
                self.last_save_time = now
            # Broadcast via WebSocket (handled by main app)
            # Sleep to match video fps
            await asyncio.sleep(1.0 / self.fps)

    def request_roi(self, polygon: Optional[list]):
        """Update ROI polygon (list of [x,y] points or list of {x,y} dicts)."""
        norm = self._normalize_polygon(polygon)
        with self._roi_lock:
            self._roi_polygon = norm

    def _normalize_polygon(self, polygon: Optional[list]) -> Optional[list]:
        if not polygon:
            return None
        pts = []
        for p in polygon:
            if isinstance(p, dict) and "x" in p and "y" in p:
                pts.append([float(p["x"]), float(p["y"])])
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                pts.append([float(p[0]), float(p[1])])
        if len(pts) < 3:
            return None
        return pts

    def _is_detection_in_roi(self, det: Dict[str, Any], polygon: list) -> bool:
        try:
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            poly = np.array(polygon, dtype=np.float32)
            # pointPolygonTest returns +1 / 0 / -1
            return cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0
        except Exception:
            return True

    def request_video_source(self, video_path: str):
        """Request switching to a new video source (applied in the pipeline loop)."""
        with self._cap_lock:
            self._pending_video_path = video_path

    def _switch_video_source(self, video_path: str):
        """Switch underlying cv2.VideoCapture (called from pipeline thread)."""
        logger.info(f"Switching video source to: {video_path}")
        try:
            with self._cap_lock:
                if self.cap:
                    self.cap.release()
                self._is_live_source = str(video_path).lower().startswith(("rtsp://", "http://", "https://"))
                if self._is_live_source:
                    self.cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
                    try:
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass
                else:
                    self.cap = cv2.VideoCapture(video_path)
                self.video_path = video_path
                self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # Reset tracker/counters to avoid mixing sources
            self.tracker = ByteTracker()
            self.frame_count = 0
            self.per_minute_counts.clear()
        except Exception as e:
            logger.exception(f"Failed to switch video source: {e}")

    async def _save_minute_metrics(self, minute_key: datetime):
        counts = dict(self.per_minute_counts.get(minute_key, {}))
        risk_count = 0
        traffic_state = compute_traffic_state(counts)
        await save_metrics(
            timestamp=minute_key.isoformat(),
            counts=counts,
            traffic_state=traffic_state,
            risk_count=risk_count
        )
        # Clean old minute data to avoid memory bloat
        if minute_key - timedelta(hours=2) in self.per_minute_counts:
            del self.per_minute_counts[minute_key - timedelta(hours=2)]

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def get_latest_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.latest_metrics) if self.latest_metrics else {}

    def stop(self):
        self.running = False
        with self._cap_lock:
            if self.cap:
                self.cap.release()
        logger.info("Pipeline stopped.")
