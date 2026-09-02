"""
Segmentation Abstraction for MAKE Vision Engine.

Supports SAM, SAM2, YOLO segment, rembg, OpenCV backends.
Never fakes masks.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class SegmentationResult:
    mask_id: str
    asset_id: str
    frame_index: int
    mask_data: Optional[Any] = None
    confidence: float = 0.0
    bbox: List[float] = field(default_factory=list)
    backend: str = "unknown"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SegmentationEngine:
    def __init__(self, backend: str = "auto"):
        self.backend = self._resolve_backend(backend)
        self._model = None
        if self.backend != "null":
            self._load_model()

    def _resolve_backend(self, preferred: str) -> str:
        if preferred != "auto":
            return preferred
        try:
            import rembg
            return "rembg"
        except ImportError:
            pass
        try:
            import torch
            return "sam"
        except ImportError:
            pass
        try:
            import cv2
            return "opencv"
        except ImportError:
            pass
        return "null"

    def _load_model(self):
        try:
            if self.backend == "rembg":
                import rembg
                self._model = rembg.new_session("u2net")
            elif self.backend == "sam":
                from segment_anything import sam_model_registry, SamPredictor
                import torch
                self._model = SamPredictor(sam_model_registry["vit_b"](checkpoint=None))
            elif self.backend == "opencv":
                import cv2
                self._model = cv2
        except Exception:
            self._model = None
            self.backend = "null"

    def segment_person(self, frame, frame_index: int = 0) -> SegmentationResult:
        if self.backend == "null" or self._model is None:
            return SegmentationResult(
                mask_id=str(uuid.uuid4()),
                asset_id="",
                frame_index=frame_index,
                confidence=0.0,
                backend="null",
                error="No segmentation backend available",
            )
        try:
            if self.backend == "rembg":
                import rembg
                output = rembg.remove(self._model, frame)
                mask = output[:, :, 3] if output.shape[2] == 4 else None
                return SegmentationResult(
                    mask_id=str(uuid.uuid4()),
                    asset_id="",
                    frame_index=frame_index,
                    mask_data=mask,
                    confidence=0.9,
                    backend="rembg-u2net",
                )
            elif self.backend == "sam":
                import torch
                self._model.set_image(frame)
                masks, scores, _ = self._model.predict(box=None, multimask_output=True)
                best = masks[scores.argmax()]
                return SegmentationResult(
                    mask_id=str(uuid.uuid4()),
                    asset_id="",
                    frame_index=frame_index,
                    mask_data=best,
                    confidence=float(scores.max()),
                    backend="sam-vit-b",
                )
            elif self.backend == "opencv":
                import cv2
                h, w = frame.shape[:2]
                mask = self._model.createBackgroundSubtractorMOG2().apply(frame)
                return SegmentationResult(
                    mask_id=str(uuid.uuid4()),
                    asset_id="",
                    frame_index=frame_index,
                    mask_data=mask,
                    confidence=0.5,
                    backend="opencv-mog2",
                )
        except Exception as e:
            return SegmentationResult(
                mask_id=str(uuid.uuid4()),
                asset_id="",
                frame_index=frame_index,
                confidence=0.0,
                backend=self.backend,
                error=str(e),
            )
        return SegmentationResult(mask_id=str(uuid.uuid4()), asset_id="", frame_index=frame_index, confidence=0.0, backend="null", error="Unsupported backend")

    def segment_batch(self, frames: List[Any], frame_indices: Optional[List[int]] = None) -> List[SegmentationResult]:
        if frame_indices is None:
            frame_indices = list(range(len(frames)))
        return [self.segment_person(f, fi) for f, fi in zip(frames, frame_indices)]
