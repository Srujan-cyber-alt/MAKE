import uuid
import asyncio
import logging
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import V2VTransformParams
from app.services.transformation_analyzer import TransformationAnalyzer
from app.services.transformation_planner import TransformationPlanner
from app.services.visual_analyzer import VisualAnalyzer
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.frame_processor import frame_processor
from app.services.video_processing import video_processing_service
from app.services.quality_gates import QualityGates
from app.services.job_graph import JobGraphEngine
from app.services.versioning import VersionWorkflow
from app.services.identity_engine import IdentityEngine
from app.services.product_consistency import ProductConsistencyService
from app.services.storage import storage_service
from app.services.redis_service import redis_service
from app.providers.registry import get_provider_registry
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.core.database import async_session_maker
from sqlalchemy import select
from app.models.models import Job, JobStatus
from datetime import datetime

logger = logging.getLogger(__name__)


class TransformationExecutor:
    @staticmethod
    async def execute_v2v(
        transformation_id: str,
        request: Dict[str, Any],
        plan_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        asset_id = request.get("source_asset_id")
        project_id = request.get("project_id")
        prompt = request.get("prompt", "")
        operations = plan_data.get("operations", [])

        source_path = await TransformationExecutor._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path:
            return {"error": "Source asset not found", "stage": "resolve"}

        analysis = await VisualAnalyzer.analyze_video(asset_id, project_id, user_id)
        detected_targets = analysis.get("objects", []) + analysis.get("faces", [])

        masks = []
        tracks = []
        for op in operations:
            op_type = op.get("type")
            target = op.get("target")
            if target:
                track = await TrackingService.track_person(
                    asset_id=asset_id,
                    frame_range=op.get("frame_range"),
                )
                tracks.append(track.model_dump())

            if op_type in ["object_removal", "object_replacement", "background_replacement"]:
                mask_type = target.get("type", "object") if target else "object"
                mask = await SegmentationService.segment_person(
                    asset_id=asset_id,
                    frame_range=op.get("frame_range"),
                )
                masks.append(mask.model_dump())

        output_path = f"/tmp/v2v_{transformation_id}.mp4"
        try:
            if video_processing_service._check_ffmpeg():
                await video_processing_service.remove_audio(source_path, output_path)
            else:
                return {"error": "ffmpeg not available for local processing", "stage": "process"}
        except Exception as e:
            logger.error(f"Local V2V processing failed: {e}")
            return {"error": f"Processing failed: {e}", "stage": "process"}

        provider_result = await TransformationExecutor._try_provider_execution(
            prompt=prompt,
            operations=operations,
            asset_id=asset_id,
            project_id=project_id,
        )
        if provider_result and not provider_result.get("error"):
            output_path = provider_result.get("output_path", output_path)

        quality = await QualityGates.evaluate(
            video_path=output_path,
            identity_required=request.get("preserve_identity", True),
            product_required=bool(request.get("references", [])),
            result_metadata={"asset_id": asset_id, "transformation_id": transformation_id},
            reference_asset_ids=request.get("references", []),
        )

        return {
            "output_path": output_path,
            "masks": masks,
            "tracks": tracks,
            "quality": quality.model_dump(),
            "provider_result": provider_result,
            "stage": "completed",
        }

    @staticmethod
    async def _try_provider_execution(
        prompt: str,
        operations: List[Dict[str, Any]],
        asset_id: str,
        project_id: str,
    ) -> Optional[Dict[str, Any]]:
        registry = get_provider_registry()
        providers = list(registry.get_all().values())

        for provider in providers:
            try:
                caps = [c.value for c in provider.get_capabilities()]
                required = ["video_to_video", "reference_images"]
                if not all(c in caps for c in required):
                    continue

                gen_request = GenerationRequest(
                    prompt=prompt,
                    duration_seconds=10,
                    aspect_ratio="16:9",
                    reference_images=[],
                    parameters={"transformation": operations},
                )
                response = await provider.submit_generation(gen_request, model_id=provider.get_supported_models()[0].id)
                return {"provider_job_id": response.provider_job_id, "status": "submitted", "provider": provider.name}
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue
        return None

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None
