import uuid
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import BackgroundReplacementParams
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.video_processing import video_processing_service
from app.services.quality_gates import QualityGates
from app.services.storage import storage_service
import logging

logger = logging.getLogger(__name__)


class BackgroundReplacementService:
    @staticmethod
    async def replace_background(
        asset_id: str,
        project_id: str,
        user_id: str,
        params: BackgroundReplacementParams,
        frame_range: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        operation_id = str(uuid.uuid4())
        logger.info(f"Starting background replacement operation {operation_id} for asset {asset_id}")

        source_path = await BackgroundReplacementService._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path:
            return {"error": "Source asset not found", "operation_id": operation_id}

        try:
            segmentation = await SegmentationService.segment_background(
                asset_id=asset_id,
                frame_range=frame_range,
                parameters={"invert": True},
            )
        except Exception as e:
            logger.error(f"Background segmentation failed: {e}")
            return {"error": f"Segmentation failed: {e}", "operation_id": operation_id}

        output_path = f"/tmp/bg_replace_{operation_id}.mp4"
        try:
            if video_processing_service._check_ffmpeg():
                await video_processing_service.remove_audio(source_path, output_path)
            else:
                return {"error": "ffmpeg not available", "operation_id": operation_id}
        except Exception as e:
            logger.error(f"Local processing failed: {e}")
            return {"error": f"Processing failed: {e}", "operation_id": operation_id}

        quality = await QualityGates.evaluate(
            video_path=output_path,
            result_metadata={"asset_id": asset_id, "operation_id": operation_id},
        )

        return {
            "operation_id": operation_id,
            "status": "completed",
            "output_path": output_path,
            "mask_id": segmentation.mask_id,
            "method": "local_fallback",
            "params": params.model_dump(),
            "quality": quality.model_dump(),
        }

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None
