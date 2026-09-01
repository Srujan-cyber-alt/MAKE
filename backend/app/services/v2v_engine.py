from typing import Optional, List, Dict, Any
from app.schemas.phase9 import V2VWorkflowRequest
from app.services.visual_analyzer import VisualAnalyzer
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.identity_lock_v2 import IdentityLockV2
from app.services.advanced_prompt_compiler import AdvancedPromptCompiler
from app.services.smart_model_router import SmartModelRouter
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.quality_gates import QualityGates
from app.services.versioning import VersionWorkflow
from app.services.transformation_executor import TransformationExecutor
from app.services.before_after import BeforeAfterComparator
from app.providers.registry import get_provider_registry
import logging

logger = logging.getLogger(__name__)


class V2VEngine:
    @staticmethod
    async def execute(request: V2VWorkflowRequest, user_id: str) -> Dict[str, Any]:
        registry = get_provider_registry()
        router = SmartModelRouter(provider_registry=registry)

        compilation = AdvancedPromptCompiler.compile_from_prompt(request.prompt)
        required_caps = []
        if request.preserve_identity:
            required_caps.append("CHARACTER_CONSISTENCY")
        if request.preserve_motion:
            required_caps.append("MOTION_TRANSFER")
        if request.strength and request.strength > 0.5:
            required_caps.append("VIDEO_TO_VIDEO")

        routing = await router.route(
            required_capabilities=required_caps,
            duration_seconds=10.0,
            aspect_ratio="16:9",
            reference_count=len(request.references),
            user_mode="quality",
        )

        analysis = await VisualAnalyzer.analyze_video(
            asset_id=request.source_asset_id,
            project_id=request.project_id,
            user_id=user_id,
        )

        masks = []
        tracks = []
        if request.preserve_identity:
            track = await TrackingService.track_person(asset_id=request.source_asset_id)
            tracks.append(track.model_dump())
            mask = await SegmentationService.segment_person(asset_id=request.source_asset_id)
            masks.append(mask.model_dump())

        executor = TransformationExecutor()
        result = await executor.execute_v2v(
            transformation_id=str(hash(request.prompt)),
            request=request.model_dump(),
            plan_data={"operations": [], "user_id": user_id},
            user_id=user_id,
        )

        quality = await QualityGates.evaluate(
            video_path=result.get("output_path", ""),
            identity_required=request.preserve_identity,
            product_required=len(request.references) > 0,
            result_metadata={"asset_id": request.source_asset_id},
            reference_asset_ids=request.references,
        )

        temporal = await TemporalConsistencyEngine.analyze(result.get("output_path", ""))

        if request.project_id and result.get("output_path"):
            try:
                await VersionWorkflow.create_version(
                    project_id=request.project_id,
                    prompt=request.prompt,
                    operations=[{"type": "v2v", "prompt": request.prompt, "preserve_motion": request.preserve_motion}],
                    asset_ids=[request.source_asset_id],
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(f"Version creation failed: {e}")

        return {
            "routing": routing,
            "compilation": compilation.model_dump(),
            "analysis": analysis,
            "masks": masks,
            "tracks": tracks,
            "execution": result,
            "quality": quality.model_dump(),
            "temporal": temporal.model_dump(),
            "status": "completed",
        }
