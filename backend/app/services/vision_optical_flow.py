"""
Optical Flow Abstraction for MAKE Vision Engine.

Supports OpenCV Farneback, TV-L1, and Null backends.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np


@dataclass
class FlowField:
    frame_index: int
    flow: Optional[np.ndarray] = None
    magnitude: float = 0.0
    direction: float = 0.0
    backend: str = "null"
    error: Optional[str] = None


class OpticalFlowEngine:
    def __init__(self, backend: str = "auto", method: str = "farneback"):
        self.backend = self._resolve_backend(backend)
        self.method = method
        self._prev_gray = None

    def _resolve_backend(self, preferred: str) -> str:
        if preferred != "auto":
            return preferred
        try:
            import cv2
            return "opencv"
        except ImportError:
            return "null"

    def compute(self, frame, frame_index: int = 0) -> FlowField:
        if self.backend == "null":
            return FlowField(frame_index=frame_index, backend="null", error="No optical flow backend available")
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            if self._prev_gray is None:
                self._prev_gray = gray
                return FlowField(frame_index=frame_index, backend=self.backend)
            flow = None
            if self.method == "farneback":
                flow = cv2.calcOpticalFlowFarneback(self._prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            elif self.method == "tvl1":
                flow = cv2.optflow.calcOpticalFlowTVL1(self._prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            self._prev_gray = gray
            if flow is not None:
                mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                return FlowField(frame_index=frame_index, flow=flow, magnitude=float(np.mean(mag)), direction=float(np.mean(ang)), backend=self.backend)
            return FlowField(frame_index=frame_index, backend=self.backend)
        except Exception as e:
            return FlowField(frame_index=frame_index, backend=self.backend, error=str(e))

    def reset(self):
        self._prev_gray = None
