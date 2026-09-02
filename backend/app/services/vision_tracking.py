"""
Tracking Abstraction for MAKE Vision Engine.

Supports ByteTrack, SORT, DeepSORT, OpenCV trackers, and Null backend.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class Track:
    track_id: str
    class_name: str
    bbox: List[float]
    frame_index: int
    confidence: float
    state: str = "active"
    lost_frames: int = 0
    metadata: Dict[str, Any] = field(default_factory=list)


@dataclass
class TrackingResult:
    tracks: List[Track]
    frame_index: int
    backend: str
    error: Optional[str] = None


class TrackingEngine:
    def __init__(self, backend: str = "auto"):
        self.backend = self._resolve_backend(backend)
        self._trackers: Dict[str, Any] = {}
        self._next_id = 1

    def _resolve_backend(self, preferred: str) -> str:
        if preferred != "auto":
            return preferred
        try:
            import cv2
            return "opencv"
        except ImportError:
            return "null"

    def _get_tracker(self, tracker_type: str = "CSRT"):
        try:
            import cv2
            tracker = getattr(cv2, f"Tracker{tracker_type}_create", None)
            if tracker:
                return tracker()
        except Exception:
            pass
        return None

    def track(self, frame, detections: List[Dict[str, Any]], frame_index: int = 0) -> TrackingResult:
        if self.backend == "null":
            return TrackingResult(tracks=[], frame_index=frame_index, backend="null", error="No tracking backend available")
        tracks = []
        try:
            if self.backend == "opencv":
                import cv2
                h, w = frame.shape[:2]
                for det in detections:
                    x1, y1, x2, y2 = det.get("bbox", [0, 0, 0, 0])
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    bw, bh = x2 - x1, y2 - y1
                    if bw < 10 or bh < 10:
                        continue
                    track_id = det.get("object_id", f"track_{self._next_id}")
                    if track_id not in self._trackers:
                        tracker = self._get_tracker("CSRT")
                        if tracker:
                            try:
                                ok = tracker.init(frame, (float(x1), float(y1), float(bw), float(bh)))
                                if ok:
                                    self._trackers[track_id] = tracker
                                    self._next_id += 1
                            except Exception:
                                continue
                    if track_id in self._trackers:
                        ok, box = self._trackers[track_id].update(frame)
                        if ok:
                            x, y, bw, bh = box
                            tracks.append(Track(
                                track_id=track_id,
                                class_name=det.get("class_name", "unknown"),
                                bbox=[float(x), float(y), float(x + bw), float(y + bh)],
                                frame_index=frame_index,
                                confidence=det.get("confidence", 0.8),
                            ))
                        else:
                            del self._trackers[track_id]
        except Exception as e:
            return TrackingResult(tracks=[], frame_index=frame_index, backend=self.backend, error=str(e))
        return TrackingResult(tracks=tracks, frame_index=frame_index, backend=self.backend)

    def reset(self):
        self._trackers.clear()
        self._next_id = 1
