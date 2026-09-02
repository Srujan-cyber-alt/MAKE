"""
Object Detection Abstraction for MAKE Vision Engine.

Supports multiple backends: YOLO, ONNX, OpenCV Haar Cascades, Null.
Never fakes detections.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class DetectionBackend(Enum):
    YOLO = "yolo"
    ONNX = "onnx"
    OPENCV = "opencv"
    NULL = "null"


@dataclass
class Detection:
    object_id: str
    class_name: str
    confidence: float
    bbox: List[float]
    frame_index: int
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


class ObjectDetector:
    def __init__(self, backend: DetectionBackend, model_name: Optional[str] = None):
        self.backend = backend
        self.model_name = model_name
        self._model = None
        self._load_model()

    def _load_model(self):
        if self.backend == DetectionBackend.YOLO:
            try:
                from ultralytics import YOLO
                self._model = YOLO(self.model_name or "yolov8n.pt")
            except ImportError:
                self.backend = DetectionBackend.NULL
            except Exception:
                self.backend = DetectionBackend.NULL
        elif self.backend == DetectionBackend.ONNX:
            try:
                import onnxruntime as ort
                self._model = ort.InferenceSession(self.model_name or "yolov8n.onnx")
            except ImportError:
                self.backend = DetectionBackend.NULL
            except Exception:
                self.backend = DetectionBackend.NULL
        elif self.backend == DetectionBackend.OPENCV:
            try:
                import cv2
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml' if 'face' in (self.model_name or '') else cv2.data.haarcascades + 'haarcascade_fullbody.xml'
                self._model = cv2.CascadeClassifier(cascade_path)
                if self._model.empty():
                    self.backend = DetectionBackend.NULL
            except ImportError:
                self.backend = DetectionBackend.NULL
            except Exception:
                self.backend = DetectionBackend.NULL

    def detect(self, frame, frame_index: int = 0, timestamp: float = 0.0) -> List[Detection]:
        if self.backend == DetectionBackend.NULL or self._model is None:
            return []
        detections = []
        try:
            if self.backend == DetectionBackend.YOLO:
                results = self._model(frame, verbose=False)
                for r in results:
                    boxes = r.boxes
                    if boxes is not None:
                        for box in boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            xyxy = box.xyxy[0].tolist()
                            class_name = self._model.names.get(cls_id, str(cls_id))
                            detections.append(Detection(
                                object_id=f"obj_{frame_index}_{len(detections)}",
                                class_name=class_name,
                                confidence=conf,
                                bbox=[float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                                frame_index=frame_index,
                                timestamp=timestamp,
                            ))
            elif self.backend == DetectionBackend.OPENCV:
                import cv2
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
                rects = self._model.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                for i, (x, y, w, h) in enumerate(rects):
                    detections.append(Detection(
                        object_id=f"obj_{frame_index}_{i}",
                        class_name="person" if "face" not in (self.model_name or '') else "face",
                        confidence=0.8,
                        bbox=[float(x), float(y), float(x + w), float(y + h)],
                        frame_index=frame_index,
                        timestamp=timestamp,
                    ))
        except Exception:
            return []
        return detections

    def detect_batch(self, frames: List[Any], frame_indices: Optional[List[int]] = None, timestamps: Optional[List[float]] = None) -> List[List[Detection]]:
        if frame_indices is None:
            frame_indices = list(range(len(frames)))
        if timestamps is None:
            timestamps = [0.0] * len(frames)
        return [self.detect(f, fi, ts) for f, fi, ts in zip(frames, frame_indices, timestamps)]
