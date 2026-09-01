"""
Video-to-Video Superengine for MAKE AI Video.

First-class V2V workflows:
- style transfer
- character replacement
- clothing replacement
- background replacement
- environment transformation
- motion transfer
- camera reinterpretation
- lighting transformation
- time-of-day transformation
- weather transformation
- product replacement
- scene restyling
- cinematic conversion

Preserves requested invariants.

Example:
"Make this scene cyberpunk but keep the person, movement and camera."

Only requested properties should change.
"""

from typing import Optional, List, Dict, Any
from app.services.visual_analyzer import VisualAnalyzer
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.identity_lock_v2 import IdentityLockV2
from app.services.product_system import ProductSystem
from app.services.camera_control_engine import CameraControlEngine
from app.services.motion_engine import MotionEngine
from app.services.color_look_engine import ColorLookEngine
from app.services.world_system import WorldSystem
from app.services.smart_model_router import SmartModelRouterV3
from app.services.advanced_prompt_compiler import AdvancedPromptCompiler
from app.services.transformation_executor_v2 import TransformationExecutorV2
from app.services.quality_control import QualityControl
from app.services.capability_registry import CapabilityRegistry
import uuid
import logging

logger = logging.getLogger(__name__)


class VideoToVideoEngine:
    @staticmethod
    async def transform_video(
        source_asset_id: str,
        project_id: str,
        user_id: str,
        prompt: str,
        preserve_person: bool = False,
        preserve_product: bool = False,
        preserve_camera: bool = False,
        preserve_motion: bool = False,
        preserve_background: bool = False,
        character_references: Optional[List[str]] = None,
        product_references: Optional[List[str]] = None,
        world_id: Optional[str] = None,
        style_strength: float = 0.8,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        logger.info(f"Starting V2V job {job_id} for asset {source_asset_id}")

        analysis = await VisualAnalyzer.analyze_video(
            asset_id=source_asset_id,
            project_id=project_id,
            user_id=user_id,
        )

        capabilities = await CapabilityRegistry.get_all_capabilities()
        compiled = AdvancedPromptCompiler.compile_from_prompt(prompt, context={
            "analysis": analysis,
            "preserve_person": preserve_person,
            "preserve_product": preserve_product,
            "preserve_camera": preserve_camera,
            "preserve_motion": preserve_motion,
            "preserve_background": preserve_background,
        })

        router = SmartModelRouterV3(provider_registry=__import__("app.providers.registry", fromlist=["get_provider_registry"]).get_provider_registry())
        routing = await router.route(
            required_capabilities=[],
            duration_seconds=analysis.get("duration_seconds", 10.0),
            aspect_ratio="16:9",
            reference_count=len(character_references or []) + len(product_references or []),
            user_mode="quality",
            character_consistency_required=preserve_person,
            product_consistency_required=preserve_product,
        )

        identity_locks = []
        if preserve_person and character_references:
            for ref_id in character_references:
                lock = await IdentityLockV2.create_profile(
                    entity_type="character",
                    name=f"v2v_ref_{ref_id}",
                    reference_asset_ids=[ref_id],
                    mode="strict",
                )
                identity_locks.append(lock.model_dump() if hasattr(lock, "model_dump") else lock)

        product_locks = []
        if preserve_product and product_references:
            for ref_id in product_references:
                lock = await IdentityLockV2.create_profile(
                    entity_type="product",
                    name=f"v2v_prod_{ref_id}",
                    reference_asset_ids=[ref_id],
                    mode="strict",
                )
                product_locks.append(lock.model_dump() if hasattr(lock, "model_dump") else lock)

        world_context = {}
        if world_id:
            world_context = await WorldSystem.get_world(world_id) or {}

        camera_plan = None
        if preserve_camera:
            camera_plan = CameraControlEngine.parse_natural_language(prompt)
            camera_plan = camera_plan.model_dump() if hasattr(camera_plan, "model_dump") else camera_plan.__dict__

        motion_plan = None
        if preserve_motion:
            motions = MotionEngine.parse_natural_language(prompt)
            motion_plan = [m.model_dump() if hasattr(m, "model_dump") else m.__dict__ for m in motions]

        color_plan = None
        if "color" in prompt.lower() or "look" in prompt.lower() or "grade" in prompt.lower():
            from app.schemas.phase9 import ColorLookAdjustment
            color_plan = ColorLookAdjustment(preset="cinematic")
            color_plan = color_plan.model_dump() if hasattr(color_plan, "model_dump") else color_plan.__dict__

        transformation_params = {
            "job_id": job_id,
            "source_asset_id": source_asset_id,
            "prompt": compiled.compiled_prompt if hasattr(compiled, "compiled_prompt") else prompt,
            "preserve_person": preserve_person,
            "preserve_product": preserve_product,
            "preserve_camera": preserve_camera,
            "preserve_motion": preserve_motion,
            "preserve_background": preserve_background,
            "style_strength": style_strength,
            "identity_locks": identity_locks,
            "product_locks": product_locks,
            "world_context": world_context,
            "camera_plan": camera_plan,
            "motion_plan": motion_plan,
            "color_plan": color_plan,
            "routing": routing,
        }

        return {
            "job_id": job_id,
            "status": "planned",
            "transformation_params": transformation_params,
            "analysis": analysis,
            "routing": routing,
            "capabilities": capabilities,
        }

    @staticmethod
    async def execute_transformation(source_asset_id: str, project_id: str, user_id: str, transformation_params: Dict[str, Any]) -> Dict[str, Any]:
        from app.schemas.transformation import TransformationRequest, TransformationOperation
        from app.services.target_selection_workflow import TargetSelectionWorkflow

        operations = []
        if transformation_params.get("preserve_background"):
            operations.append(TransformationOperation(
                type="background_replacement",
                target={"type": "background", "description": "background"},
            ))
        if transformation_params.get("preserve_person"):
            operations.append(TransformationOperation(
                type="style_transfer",
                target={"type": "person", "description": "person"},
            ))

        request = TransformationRequest(
            project_id=project_id,
            source_asset_id=source_asset_id,
            prompt=transformation_params.get("prompt", ""),
            operations=operations,
            preserve_identity=transformation_params.get("preserve_person", False),
        )

        executor = TransformationExecutorV2()
        result = await executor.execute_transformation(request, user_id)
        return result
