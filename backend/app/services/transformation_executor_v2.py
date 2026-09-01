"""
Real Transformation Execution with Provider Routing.

Wires together:
- Segmentation
- Tracking
- Identity Lock
- Quality Gates
- Provider execution
- Fallback chains
- Shot repair
- Versioning
"""

from typing import Optional, List, Dict, Any
from app.schemas.transformation import TransformationRequest, TransformationOperation
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.identity_lock_v2 import IdentityLockV2
from app.services.quality_gates import QualityGates
from app.services.shot_repair_engine import ShotRepairEngine
from app.services.versioning import VersionWorkflow
from app.services.transformation_executor import TransformationExecutor
from app.services.before_after import BeforeAfterComparator
from app.services.visual_analyzer import VisualAnalyzer
from app.services.smart_model_router import SmartModelRouter
from app.services.generative_model_abstraction import GenerativeModelAbstraction
from app.providers.registry import get_provider_registry
from app.services.redis_service import redis_service
import uuid
import logging

logger = logging.getLogger(__name__)


class TransformationExecutorV2:
    @staticmethod
    async def execute_transformation(
        request: TransformationRequest,
        user_id: str,
        pipeline_state: Optional[Any] = None,
    ) -> Dict[str, Any]:
        transformation_id = str(uuid.uuid4())
        logger.info(f"Starting transformation {transformation_id} for project {request.project_id}")

        analysis = await VisualAnalyzer.analyze_video(
            asset_id=request.source_asset_id,
            project_id=request.project_id,
            user_id=user_id,
        )

        registry = get_provider_registry()
        router = SmartModelRouter(provider_registry=registry)

        required_caps = []
        for op in request.operations:
            op_type = op.type.value if hasattr(op.type, "value") else str(op.type)
            cap_map = {
                "object_removal": "INPAINTING",
                "object_replacement": "INPAINTING",
                "background_replacement": "BACKGROUND_REPLACEMENT",
                "motion_transfer": "MOTION_TRANSFER",
                "style_transfer": "STYLE_TRANSFER",
                "video_to_video": "VIDEO_TO_VIDEO",
                "inpainting": "INPAINTING",
                "outpainting": "OUTPAINTING",
                "camera_transform": "CAMERA_CONTROL",
            }
            if op_type in cap_map:
                required_caps.append(cap_map[op_type])

        routing = {}
        if required_caps:
            routing = await router.route(
                required_capabilities=required_caps,
                duration_seconds=10.0,
                aspect_ratio="16:9",
                reference_count=len(request.references or []),
                user_mode="quality",
            )

        segmentation_results = []
        tracking_results = []
        identity_locks = []

        for op in request.operations:
            target = op.target
            if not target:
                continue

            target_desc = target.description or target.type
            if target.type in ("person", "object", "background", "face", "product"):
                seg = await SegmentationService.segment_object(
                    asset_id=request.source_asset_id,
                    object_label=target_desc,
                    frame_range=op.frame_range,
                )
                segmentation_results.append(seg.model_dump())

            if target.type in ("person", "object", "product", "vehicle"):
                track = await TrackingService.track_person(
                    asset_id=request.source_asset_id,
                    frame_range=op.frame_range,
                )
                tracking_results.append(track.model_dump())

            if request.preserve_identity and target.type in ("person", "face"):
                lock = await IdentityLockV2.create_profile(
                    entity_type=target.type,
                    name=target_desc,
                    reference_asset_ids=request.references or [],
                    mode="balanced",
                )
                identity_locks.append(lock.model_dump())

        executor = TransformationExecutor()
        result = await executor.execute_v2v(
            transformation_id=transformation_id,
            request=request.model_dump(),
            plan_data={"operations": [op.model_dump() for op in request.operations], "user_id": user_id},
            user_id=user_id,
        )

        output_path = result.get("output_path", "")
        quality = await QualityGates.evaluate(
            video_path=output_path,
            identity_required=request.preserve_identity,
            product_required=bool(request.references),
            result_metadata={"asset_id": request.source_asset_id, "transformation_id": transformation_id},
            reference_asset_ids=request.references or [],
        )

        repair_result = None
        if not quality.passed and pipeline_state:
            repair_result = await TransformationExecutorV2._attempt_repair(
                transformation_id=transformation_id,
                quality_result=quality,
                output_path=output_path,
                request=request,
                user_id=user_id,
            )

        if request.project_id and output_path:
            try:
                await VersionWorkflow.create_version(
                    project_id=request.project_id,
                    prompt=request.prompt,
                    operations=[op.model_dump() for op in request.operations],
                    asset_ids=[request.source_asset_id],
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(f"Version creation failed: {e}")

        return {
            "transformation_id": transformation_id,
            "status": "completed" if quality.passed else "completed_with_issues",
            "output_path": output_path,
            "routing": routing,
            "segmentation": segmentation_results,
            "tracking": tracking_results,
            "identity_locks": identity_locks,
            "quality": quality.model_dump(),
            "repair": repair_result,
            "analysis": analysis,
        }

    @staticmethod
    async def _attempt_repair(
        transformation_id: str,
        quality_result: Any,
        output_path: str,
        request: TransformationRequest,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            diagnosis = await ShotRepairEngine.diagnose(
                shot_id=transformation_id,
                video_path=output_path,
            )
            if diagnosis.get("severity") in ("high", "critical"):
                repair = await ShotRepairEngine.repair(
                    request=type("RepairRequest", (), {
                        "shot_id": transformation_id,
                        "repair_type": "temporal",
                        "frame_range": None,
                        "parameters": {"strategy": diagnosis.get("repair_strategies", [{}])[0] if diagnosis.get("repair_strategies") else {}},
                        "priority": "high",
                    })(),
                    video_path=output_path,
                )
                return {"diagnosis": diagnosis, "repair": repair}
        except Exception as e:
            logger.warning(f"Auto-repair failed: {e}")
        return None
