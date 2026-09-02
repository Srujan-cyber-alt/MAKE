"""
Pose Estimation Abstraction for MAKE Vision Engine.

Supports OpenCV (upper body) and Null backends.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Keypoint:
    x: float
    y: float
    confidence: float
    name: str


@dataclass
class Pose:
    frame_index: int
    timestamp: float
    keypoints: List[Keypoint]
    backend: str
    confidence: float = 0.0
    error: Optional[str] = None


class PoseEstimator:
    def __init__(self, backend: str = "auto"):
        self.backend = self._resolve_backend(backend)
        self._model = None
        if self.backend != "null":
            self._load_model()

    def _resolve_backend(self, preferred: str) -> str:
        if preferred != "auto":
            return preferred
        try:
            import cv2
            return "opencv"
        except ImportError:
            return "null"

    def _load_model(self):
        if self.backend == "opencv":
            try:
                import cv2
                proto = cv2.data.haarcascades + 'haarcascade_upperbody.xml'
                self._model = cv2.CascadeClassifier(proto)
            except Exception:
                self._model = None
                self.backend = "null"

    def estimate(self, frame, frame_index: int = 0, timestamp: float = 0.0) -> Pose:
        if self.backend == "null" or self._model is None:
            return Pose(frame_index=frame_index, timestamp=timestamp, keypoints=[], backend="null", confidence=0.0, error="No pose backend available")
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            bodies = self._model.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            if len(bodies) == 0:
                return Pose(frame_index=frame_index, timestamp=timestamp, keypoints=[], backend=self.backend, confidence=0.0)
            x, y, w, h = bodies[0]
            keypoints = [
                Keypoint(x=x + w * 0.5, y=y + h * 0.1, confidence=0.7, name="head"),
                Keypoint(x=x + w * 0.5, y=y + h * 0.3, confidence=0.7, name="chest"),
                Keypoint(x=x + w * 0.3, y=y + h * 0.3, confidence=0.6, name="left_shoulder"),
                Keypoint(x=x + w * 0.7, y=y + h * 0.3, confidence=0.6, name="right_shoulder"),
                Keypoint(x=x + w * 0.3, y=y + h * 0.55, confidence=0.6, name="left_elbow"),
                Keypoint(x=x + w * 0.7, y=y + h * 0.55, confidence=0.6, name="right_elbow"),
                Keypoint(x=x + w * 0.3, y=y + h * 0.75, confidence=0.5, name="left_wrist"),
                Keypoint(x=x + w * 0.7, y=y + h * 0.75, confidence=0.5, name="right_wrist"),
            ]
            return Pose(frame_index=frame_index, timestamp=timestamp, keypoints=keypoints, backend=self.backend, confidence=0.7)
        except Exception as e:
            return Pose(frame_index=frame_index, timestamp=timestamp, keypoints=[], backend=self.backend, confidence=0.0, error=str(e))

    def estimate_batch(self, frames: List[Any], frame_indices: Optional[List[int]] = None, timestamps: Optional[List[float]] = None) -> List[Pose]:
        if frame_indices is None:
            frame_indices = list(range(len(frames)))
        if timestamps is None:
            timestamps = [0.0] * len(frames)
        return [self.estimate(f, fi, ts) for f, fi, ts in zip(frames, frame_indices, timestamps)]
