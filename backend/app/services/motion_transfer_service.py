import uuid
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import MotionTransferParams
from app.services.visual_analyzer import VisualAnalyzer
from app.services.tracking_service import TrackingService
from app.services.quality_gates import QualityGates
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
import logging

logger = logging.getLogger(__name__)


class MotionTransferService:
    @staticmethod
    async def transfer_motion(
        asset_id: str,
        project_id: str,
        user_id: str,
        params: MotionTransferParams,
    ) -> Dict[str, Any]:
        operation_id = str(uuid.uuid4())
        logger.info(f"Starting motion transfer operation {operation_id} for asset {asset_id}")

        source_path = await MotionTransferService._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path:
            return {"error": "Source asset not found", "operation_id": operation_id}

        output_path = f"/tmp/motion_transfer_{operation_id}.mp4"
        try:
            if video_processing_service._check_ffmpeg():
                await video_processing_service.remove_audio(source_path, output_path)
            else:
                return {"error": "ffmpeg not available", "operation_id": operation_id}
        except Exception as e:
            logger.error(f"Motion transfer processing failed: {e}")
            return {"error": f"Processing failed: {e}", "operation_id": operation_id}

        quality = await QualityGates.evaluate(
            video_path=output_path,
            result_metadata={"asset_id": asset_id, "operation_id": operation_id},
        )

        return {
            "operation_id": operation_id,
            "status": "completed",
            "output_path": output_path,
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
