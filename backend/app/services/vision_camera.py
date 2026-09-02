"""
Camera Motion Analysis for MAKE Vision Engine.

Analyzes camera movement from frame-to-frame analysis.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import math


@dataclass
class CameraMotion:
    motion_type: str
    confidence: float
    intensity: str
    trajectory: List[Dict[str, float]]
    backend: str
    error: Optional[str] = None


class CameraMotionAnalyzer:
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

    def analyze(self, frames: List[Any]) -> CameraMotion:
        if self.backend == "null" or len(frames) < 2:
            return CameraMotion(motion_type="static", confidence=0.0, intensity="low", trajectory=[], backend="null", error="Insufficient frames or no backend")
        try:
            import cv2
            import numpy as np
            prev_gray = None
            dx_total = 0.0
            dy_total = 0.0
            trajectory = []
            for i in range(1, len(frames)):
                curr = frames[i]
                curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY) if len(curr.shape) == 3 else curr
                if prev_gray is not None:
                    flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                    dx = float(np.mean(flow[..., 0]))
                    dy = float(np.mean(flow[..., 1]))
                    dx_total += dx
                    dy_total += dy
                    trajectory.append({"frame": i, "dx": dx, "dy": dy})
                prev_gray = curr_gray
            avg_dx = dx_total / len(trajectory) if trajectory else 0.0
            avg_dy = dy_total / len(trajectory) if trajectory else 0.0
            magnitude = math.sqrt(avg_dx ** 2 + avg_dy ** 2)
            motion_type = "static"
            if magnitude > 5.0:
                motion_type = "handheld" if abs(avg_dx) > abs(avg_dy) * 1.5 else "panning"
            elif magnitude > 2.0:
                motion_type = "static"
            intensity = "low"
            if magnitude > 8.0:
                intensity = "high"
            elif magnitude > 3.0:
                intensity = "medium"
            return CameraMotion(motion_type=motion_type, confidence=min(magnitude / 10.0, 1.0), intensity=intensity, trajectory=trajectory, backend=self.backend)
        except Exception as e:
            return CameraMotion(motion_type="static", confidence=0.0, intensity="low", trajectory=[], backend=self.backend, error=str(e))
