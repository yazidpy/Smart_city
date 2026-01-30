import numpy as np
from typing import List, Dict, Any, Tuple
from collections import defaultdict, deque

class ByteTracker:
    """
    Simplified ByteTrack-like tracker for multi-object tracking.
    Uses IoU-based matching and simple Kalman-like state propagation.
    """
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.3):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self.tracks = {}  # track_id -> dict with state
        self.next_id = 1
        self.frame_count = 0

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        detections: list of dicts with keys: cls, conf, bbox (x1,y1,x2,y2)
        Returns: list of tracked objects with added 'track_id'
        """
        self.frame_count += 1
        # Prepare detection boxes
        det_boxes = np.array([d["bbox"] for d in detections])
        det_scores = np.array([d["conf"] for d in detections])
        det_classes = np.array([d["cls"] for d in detections])
        # Predict existing tracks (simple constant velocity)
        for track_id, track in self.tracks.items():
            self._predict(track)
        # Try to match detections to existing tracks
        matched_det_indices, matched_track_ids = self._match_detections_to_tracks(det_boxes)
        # Update matched tracks
        tracked_objects = []
        for det_idx, track_id in zip(matched_det_indices, matched_track_ids):
            track = self.tracks[track_id]
            track["bbox"] = det_boxes[det_idx].tolist()
            track["conf"] = float(det_scores[det_idx])
            track["cls"] = int(det_classes[det_idx])
            track["lost"] = 0
            track["last_seen"] = self.frame_count
            tracked_objects.append({
                "cls": track["cls"],
                "conf": track["conf"],
                "bbox": track["bbox"],
                "track_id": track_id
            })
        # Mark unmatched tracks as lost
        matched_dets_set = set(matched_det_indices)
        for track_id in self.tracks:
            if track_id not in matched_track_ids:
                self.tracks[track_id]["lost"] += 1
        # Remove tracks lost for too long
        to_delete = [tid for tid, tr in self.tracks.items() if tr["lost"] > self.max_lost]
        for tid in to_delete:
            del self.tracks[tid]
        # Initialize new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in matched_dets_set:
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = {
                    "bbox": det["bbox"],
                    "conf": det["conf"],
                    "cls": det["cls"],
                    "lost": 0,
                    "last_seen": self.frame_count,
                    "vx": 0.0,  # velocity x
                    "vy": 0.0   # velocity y
                }
                tracked_objects.append({
                    "cls": det["cls"],
                    "conf": det["conf"],
                    "bbox": det["bbox"],
                    "track_id": track_id
                })
        return tracked_objects

    def _predict(self, track: Dict[str, Any]):
        """Simple constant velocity prediction"""
        dt = 1.0  # assume 1 frame interval
        x1, y1, x2, y2 = track["bbox"]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        # Update center with velocity
        cx += track["vx"] * dt
        cy += track["vy"] * dt
        # Update bbox
        track["bbox"] = [cx - w/2, cy - h/2, cx + w/2, cy + h/2]

    def _match_detections_to_tracks(self, det_boxes: np.ndarray) -> Tuple[List[int], List[int]]:
        """IoU-based matching between detections and active tracks"""
        if len(det_boxes) == 0 or len(self.tracks) == 0:
            return [], []
        # Build track boxes
        track_ids = list(self.tracks.keys())
        track_boxes = np.array([self.tracks[tid]["bbox"] for tid in track_ids])
        # Compute IoU matrix
        iou_matrix = self._iou_batch(det_boxes, track_boxes)
        # Hungarian matching (greedy for simplicity)
        matched_det = []
        matched_track = []
        used_dets = set()
        used_tracks = set()
        # Greedy assignment by highest IoU
        while True:
            # Find best remaining pair
            best_iou = 0
            best_det = None
            best_track = None
            for i in range(len(det_boxes)):
                if i in used_dets:
                    continue
                for j, tid in enumerate(track_ids):
                    if tid in used_tracks:
                        continue
                    if iou_matrix[i, j] > best_iou:
                        best_iou = iou_matrix[i, j]
                        best_det = i
                        best_track = tid
            if best_iou < self.iou_threshold or best_det is None:
                break
            matched_det.append(best_det)
            matched_track.append(best_track)
            used_dets.add(best_det)
            used_tracks.add(best_track)
        return matched_det, matched_track

    def _iou_batch(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """Compute IoU between two sets of boxes"""
        # boxes: Nx4 (x1,y1,x2,y2)
        xx1 = np.maximum(boxes1[:, None, 0], boxes2[None, :, 0])
        yy1 = np.maximum(boxes1[:, None, 1], boxes2[None, :, 1])
        xx2 = np.minimum(boxes1[:, None, 2], boxes2[None, :, 2])
        yy2 = np.minimum(boxes1[:, None, 3], boxes2[None, :, 3])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
        area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
        iou = inter / (area1[:, None] + area2[None, :] - inter + 1e-6)
        return iou
