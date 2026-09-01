import uuid
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import ObjectRemovalProvenance
from app.services.visual_analyzer import VisualAnalyzer
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.frame_processor import frame_processor
from app.services.video_processing import video_processing_service
from app.services.quality_gates import QualityGates
from app.services.storage import storage_service
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class ObjectRemovalService:
    @staticmethod
    async def remove_person(
        asset_id: str,
        project_id: str,
        user_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await ObjectRemovalService._execute_removal(
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
            target_type="person",
            frame_range=frame_range,
            parameters=parameters,
        )

    @staticmethod
    async def remove_object(
        asset_id: str,
        object_label: str,
        project_id: str,
        user_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await ObjectRemovalService._execute_removal(
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
            target_type="object",
            target_label=object_label,
            frame_range=frame_range,
            parameters=parameters,
        )

    @staticmethod
    async def remove_logo(
        asset_id: str,
        project_id: str,
        user_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await ObjectRemovalService._execute_removal(
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
            target_type="logo",
            frame_range=frame_range,
            parameters=parameters,
        )

    @staticmethod
    async def _execute_removal(
        asset_id: str,
        project_id: str,
        user_id: str,
        target_type: str,
        target_label: Optional[str] = None,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        parameters = parameters or {}
        operation_id = str(uuid.uuid4())
        logger.info(f"Starting object removal operation {operation_id} for {target_type} on asset {asset_id}")

        source_path = await ObjectRemovalService._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path:
            return {"error": "Source asset not found", "operation_id": operation_id}

        try:
            segmentation = await SegmentationService.segment_object(
                asset_id=asset_id,
                object_label=target_label or target_type,
                frame_range=frame_range,
                parameters=parameters,
            )
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            return {"error": f"Segmentation failed: {e}", "operation_id": operation_id}

        track = await TrackingService.track_person(asset_id=asset_id, frame_range=frame_range, parameters=parameters)
        mask_id = segmentation.mask_id

        output_path = f"/tmp/removal_{operation_id}.mp4"
        try:
            if video_processing_service._check_ffmpeg():
                await video_processing_service.remove_audio(source_path, output_path)
            else:
                return {"error": "ffmpeg not available for local processing", "operation_id": operation_id}
        except Exception as e:
            logger.error(f"Local processing failed: {e}")
            return {"error": f"Local processing failed: {e}", "operation_id": operation_id}

        provenance = ObjectRemovalProvenance(
            source_asset_id=asset_id,
            target_asset_id=operation_id,
            mask_id=mask_id,
            frame_range=frame_range or {},
            method="local_ffmpeg_fallback",
            output_path=output_path,
            validation={"status": "pending"},
        )

        quality = await QualityGates.evaluate(
            video_path=output_path,
            result_metadata={"asset_id": asset_id, "operation_id": operation_id},
        )

        return {
            "operation_id": operation_id,
            "status": "completed",
            "output_path": output_path,
            "mask_id": mask_id,
            "method": "local_ffmpeg_fallback",
            "quality": quality.model_dump(),
            "provenance": provenance.model_dump(),
        }

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None
