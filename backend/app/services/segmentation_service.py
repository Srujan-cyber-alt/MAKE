import uuid
import asyncio
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import (
    SegmentationResult,
    MLBackendStatus,
    SegmentationModel,
)
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class SegmentationService:
    SEGMENTATION_MODELS = {
        SegmentationModel.SAM: {"requires_gpu": True, "memory_mb": 4000, "installed": False},
        SegmentationModel.SAM2: {"requires_gpu": True, "memory_mb": 6000, "installed": False},
        SegmentationModel.YOLO: {"requires_gpu": False, "memory_mb": 1000, "installed": False},
        SegmentationModel.YOLO_WORLD: {"requires_gpu": False, "memory_mb": 1500, "installed": False},
        SegmentationModel.GROUNDING_DINO: {"requires_gpu": True, "memory_mb": 3000, "installed": False},
        SegmentationModel.REMBG: {"requires_gpu": False, "memory_mb": 500, "installed": False},
    }

    @staticmethod
    async def check_backends() -> Dict[str, MLBackendStatus]:
        backends = {}
        try:
            import torch
            backends["sam"] = MLBackendStatus.AVAILABLE
            backends["yolo"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["sam"] = MLBackendStatus.NOT_INSTALLED
            backends["yolo"] = MLBackendStatus.NOT_INSTALLED

        try:
            import cv2
            backends["opencv"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["opencv"] = MLBackendStatus.NOT_INSTALLED

        try:
            import rembg
            backends["rembg"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["rembg"] = MLBackendStatus.NOT_INSTALLED

        return backends

    @staticmethod
    async def segment_person(
        asset_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        mask_id = str(uuid.uuid4())
        parameters = parameters or {}
        backends = await SegmentationService.check_backends()

        if backends.get("rembg") == MLBackendStatus.AVAILABLE:
            try:
                import rembg
                source_path = await SegmentationService._resolve_asset_path(asset_id)
                if source_path:
                    result = SegmentationResult(
                        mask_id=mask_id,
                        target_id="person",
                        type="person",
                        confidence=0.0,
                        parameters={
                            "feather": parameters.get("feather", 2),
                            "expand": parameters.get("expand", 0),
                            "invert": parameters.get("invert", False),
                            "frame_range": frame_range,
                            "model": "rembg",
                            "backend": "rembg",
                            "status": "rembg_available",
                            "note": "RMBG backend available. Full mask generation requires integration.",
                        },
                        model="rembg",
                        generated_by="segmentation_service_v2",
                    )
                    return result
            except Exception as e:
                logger.warning(f"RMBG segmentation failed: {e}")

        result = SegmentationResult(
            mask_id=mask_id,
            target_id="person",
            type="person",
            confidence=0.0,
            parameters={
                "feather": parameters.get("feather", 2),
                "expand": parameters.get("expand", 0),
                "invert": parameters.get("invert", False),
                "frame_range": frame_range,
                "model": None,
                "backend": "none",
                "status": "no_backend",
                "note": "No segmentation backend available. Install rembg, torch, or opencv for real segmentation.",
            },
            model=None,
            generated_by="segmentation_service_v2",
        )
        return result

    @staticmethod
    async def segment_object(
        asset_id: str,
        object_label: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        mask_id = str(uuid.uuid4())
        parameters = parameters or {}
        backends = await SegmentationService.check_backends()

        if backends.get("yolo") == MLBackendStatus.AVAILABLE:
            result = SegmentationResult(
                mask_id=mask_id,
                target_id=object_label,
                type="object",
                confidence=0.0,
                parameters={
                    "label": object_label,
                    "feather": parameters.get("feather", 2),
                    "expand": parameters.get("expand", 0),
                    "invert": parameters.get("invert", False),
                    "frame_range": frame_range,
                    "model": "yolo",
                    "backend": "yolo",
                    "status": "yolo_available",
                    "note": "YOLO backend available. Full object segmentation requires model weights and integration.",
                },
                model="yolo",
                generated_by="segmentation_service_v2",
            )
            return result

        result = SegmentationResult(
            mask_id=mask_id,
            target_id=object_label,
            type="object",
            confidence=0.0,
            parameters={
                "label": object_label,
                "feather": parameters.get("feather", 2),
                "expand": parameters.get("expand", 0),
                "invert": parameters.get("invert", False),
                "frame_range": frame_range,
                "model": None,
                "backend": "none",
                "status": "no_backend",
                "note": "No object segmentation backend available. Install ultralytics for YOLO.",
            },
            model=None,
            generated_by="segmentation_service_v2",
        )
        return result

    @staticmethod
    async def segment_background(
        asset_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        mask_id = str(uuid.uuid4())
        parameters = parameters or {}
        backends = await SegmentationService.check_backends()

        if backends.get("rembg") == MLBackendStatus.AVAILABLE:
            result = SegmentationResult(
                mask_id=mask_id,
                target_id="background",
                type="background",
                confidence=0.0,
                parameters={
                    "feather": parameters.get("feather", 2),
                    "expand": parameters.get("expand", 0),
                    "invert": parameters.get("invert", True),
                    "frame_range": frame_range,
                    "model": "rembg",
                    "backend": "rembg",
                    "status": "rembg_available",
                    "note": "RMBG backend available. Background segmentation requires integration.",
                },
                model="rembg",
                generated_by="segmentation_service_v2",
            )
            return result

        result = SegmentationResult(
            mask_id=mask_id,
            target_id="background",
            type="background",
            confidence=0.0,
            parameters={
                "feather": parameters.get("feather", 2),
                "expand": parameters.get("expand", 0),
                "invert": parameters.get("invert", True),
                "frame_range": frame_range,
                "model": None,
                "backend": "none",
                "status": "no_backend",
                "note": "No background segmentation backend available.",
            },
            model=None,
            generated_by="segmentation_service_v2",
        )
        return result

    @staticmethod
    async def segment_by_point(
        asset_id: str,
        point: Dict[str, float],
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        mask_id = str(uuid.uuid4())
        backends = await SegmentationService.check_backends()
        model = "sam" if backends.get("sam") == MLBackendStatus.AVAILABLE else None
        return SegmentationResult(
            mask_id=mask_id,
            target_id="point",
            type="point",
            confidence=0.0,
            bbox={"x": point.get("x"), "y": point.get("y")},
            parameters={
                "point": point,
                "frame_range": frame_range,
                "model": model,
                "backend": model or "none",
                "status": f"{model}_available" if model else "no_backend",
                **(parameters or {})
            },
            model=model,
            generated_by="segmentation_service_v2",
        )

    @staticmethod
    async def segment_by_box(
        asset_id: str,
        bbox: Dict[str, Any],
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SegmentationResult:
        mask_id = str(uuid.uuid4())
        backends = await SegmentationService.check_backends()
        model = "sam" if backends.get("sam") == MLBackendStatus.AVAILABLE else None
        return SegmentationResult(
            mask_id=mask_id,
            target_id="box",
            type="box",
            confidence=0.0,
            bbox=bbox,
            parameters={
                "bbox": bbox,
                "frame_range": frame_range,
                "model": model,
                "backend": model or "none",
                "status": f"{model}_available" if model else "no_backend",
                **(parameters or {})
            },
            model=model,
            generated_by="segmentation_service_v2",
        )

    @staticmethod
    async def propagate_mask(
        mask_id: str,
        asset_id: str,
        frame_range: Dict[str, int],
        reference_frame: int,
    ) -> List[SegmentationResult]:
        results = []
        backends = await SegmentationService.check_backends()
        model = "sam2" if backends.get("sam") == MLBackendStatus.AVAILABLE else None
        for i in range(3):
            results.append(SegmentationResult(
                mask_id=str(uuid.uuid4()),
                target_id="propagated",
                type="propagated",
                confidence=0.0,
                parameters={
                    "note": f"{model} propagation available but not integrated." if model else "No propagation backend available.",
                    "frame_range": frame_range,
                    "reference_frame": reference_frame,
                    "model": model,
                    "backend": model or "none",
                    "status": f"{model}_available" if model else "no_backend",
                },
                generated_by="segmentation_service_v2",
            ))
        return results

    @staticmethod
    async def generate_mask_sequence(
        asset_id: str,
        target_description: str,
        frame_range: Dict[str, int],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[SegmentationResult]:
        parameters = parameters or {}
        mask = await SegmentationService.segment_object(
            asset_id=asset_id,
            object_label=target_description,
            frame_range=frame_range,
            parameters=parameters,
        )
        return [mask]

    @staticmethod
    async def _resolve_asset_path(asset_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, "", "")
        except Exception:
            return None
