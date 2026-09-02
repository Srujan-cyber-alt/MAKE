"""
Motion Extraction for MAKE Vision Engine.

Combines tracking, pose, and frame differencing to extract motion.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MotionVector:
    frame_index: int
    timestamp: float
    dx: float
    dy: float
    magnitude: float
    direction: float
    subject_id: Optional[str] = None
    confidence: float = 0.0


@dataclass
class MotionAnalysis:
    vectors: List[MotionVector]
    average_magnitude: float
    average_direction: float
    motion_type: str
    intensity: str
    backend: str
    error: Optional[str] = None


class MotionExtractor:
    def __init__(self, backend: str = "auto"):
        self.backend = self._resolve_backend(backend)

    def _resolve_backend(self, preferred: str) -> str:
        if preferred != "auto":
            return preferred
        try:
            import cv2
            return "opencv"
        except ImportError:
            return "null"

    def extract(self, frames: List[Any], frame_indices: Optional[List[int]] = None, timestamps: Optional[List[float]] = None, tracks: Optional[List[Dict]] = None) -> MotionAnalysis:
        if self.backend == "null" or len(frames) < 2:
            return MotionAnalysis(vectors=[], average_magnitude=0.0, average_direction=0.0, motion_type="static", intensity="low", backend="null", error="Insufficient frames or no backend")
        vectors = []
        try:
            import cv2
            import numpy as np
            prev_gray = None
            for i in range(1, len(frames)):
                curr = frames[i]
                curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY) if len(curr.shape) == 3 else curr
                if prev_gray is not None:
                    flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    avg_mag = float(np.mean(mag))
                    avg_ang = float(np.mean(ang))
                    vectors.append(MotionVector(
                        frame_index=frame_indices[i] if frame_indices else i,
                        timestamp=timestamps[i] if timestamps else 0.0,
                        dx=float(np.mean(flow[..., 0])),
                        dy=float(np.mean(flow[..., 1])),
                        magnitude=avg_mag,
                        direction=avg_ang,
                        confidence=min(avg_mag / 10.0, 1.0),
                    ))
                prev_gray = curr_gray
        except Exception as e:
            return MotionAnalysis(vectors=[], average_magnitude=0.0, average_direction=0.0, motion_type="static", intensity="low", backend=self.backend, error=str(e))
        avg_mag = sum(v.magnitude for v in vectors) / len(vectors) if vectors else 0.0
        avg_dir = sum(v.direction for v in vectors) / len(vectors) if vectors else 0.0
        motion_type = "static"
        intensity = "low"
        if avg_mag > 8.0:
            motion_type = "high_motion"
            intensity = "high"
        elif avg_mag > 3.0:
            motion_type = "moderate_motion"
            intensity = "medium"
        return MotionAnalysis(vectors=vectors, average_magnitude=avg_mag, average_direction=avg_dir, motion_type=motion_type, intensity=intensity, backend=self.backend)
