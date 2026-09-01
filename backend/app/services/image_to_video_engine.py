"""
Image-to-Video Superengine for MAKE AI Video.

Creates the strongest possible image-to-video workflow.

Input:
- one image
- multiple images
- character reference
- product reference
- environment reference
- style reference

Controls:
- camera movement
- subject movement
- facial movement
- body movement
- environmental motion
- depth
- lighting
- lens
- composition
- speed
- duration
- keyframes

Natural language must control all of them.
"""

from typing import Optional, List, Dict, Any
from app.services.visual_analyzer import VisualAnalyzer
from app.services.camera_control_engine import CameraControlEngine
from app.services.motion_engine import MotionEngine
from app.services.keyframe_system_v2 import KeyframeSystemV2
from app.services.smart_model_router import SmartModelRouterV3
from app.services.advanced_prompt_compiler import AdvancedPromptCompiler
from app.services.identity_lock_v2 import IdentityLockV2
from app.services.world_system import WorldSystem
from app.services.brand_dna import BrandDNA
import uuid
import logging

logger = logging.getLogger(__name__)


class ImageToVideoEngine:
    @staticmethod
    async def create_video_from_image(
        source_asset_id: str,
        project_id: str,
        user_id: str,
        prompt: str,
        duration_seconds: float = 5.0,
        camera_direction: Optional[str] = None,
        motion_direction: Optional[str] = None,
        character_references: Optional[List[str]] = None,
        product_references: Optional[List[str]] = None,
        world_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        keyframes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        logger.info(f"Starting image-to-video job {job_id} for asset {source_asset_id}")

        analysis = await VisualAnalyzer.analyze_video(
            asset_id=source_asset_id,
            project_id=project_id,
            user_id=user_id,
        )

        camera = CameraControlEngine.parse_natural_language(camera_direction or prompt)
        motion = MotionEngine.parse_natural_language(motion_direction or prompt)
        compiled_prompt = AdvancedPromptCompiler.compile_from_prompt(prompt, context={
            "source_asset_id": source_asset_id,
            "analysis": analysis,
            "camera": camera.model_dump() if hasattr(camera, "model_dump") else camera.__dict__,
            "motion": [m.model_dump() if hasattr(m, "model_dump") else m.__dict__ for m in motion],
        })

        identity_constraints = {}
        if character_references:
            for ref_id in character_references:
                lock = await IdentityLockV2.create_profile(
                    entity_type="character",
                    name=f"ref_{ref_id}",
                    reference_asset_ids=[ref_id],
                    mode="strict",
                )
                identity_constraints[ref_id] = lock.model_dump() if hasattr(lock, "model_dump") else lock

        world_context = {}
        if world_id:
            world_context = await WorldSystem.get_world(world_id) or {}

        brand_constraints = {}
        if brand_id:
            brand = await BrandDNA.get_brand_dna(brand_id)
            if brand:
                brand_constraints = brand

        router = SmartModelRouterV3(provider_registry=__import__("app.providers.registry", fromlist=["get_provider_registry"]).get_provider_registry())
        routing = await router.route(
            required_capabilities=[],
            duration_seconds=duration_seconds,
            aspect_ratio="16:9",
            reference_count=len(character_references or []) + len(product_references or []),
            user_mode="quality",
            character_consistency_required=bool(character_references),
            product_consistency_required=bool(product_references),
        )

        generation_params = {
            "job_id": job_id,
            "source_asset_id": source_asset_id,
            "prompt": compiled_prompt.compiled_prompt if hasattr(compiled_prompt, "compiled_prompt") else prompt,
            "duration_seconds": duration_seconds,
            "camera": camera.model_dump() if hasattr(camera, "model_dump") else camera.__dict__,
            "motion": [m.model_dump() if hasattr(m, "model_dump") else m.__dict__ for m in motion],
            "identity_constraints": identity_constraints,
            "world_context": world_context,
            "brand_constraints": brand_constraints,
            "keyframes": keyframes or [],
            "routing": routing,
        }

        return {
            "job_id": job_id,
            "status": "planned",
            "generation_params": generation_params,
            "analysis": analysis,
            "routing": routing,
        }

    @staticmethod
    async def plan_keyframes_from_prompt(prompt: str, duration_seconds: float) -> List[Dict[str, Any]]:
        keyframes = KeyframeSystemV2.parse_natural_language(prompt, 0, int(duration_seconds * 30))
        return [k.model_dump() if hasattr(k, "model_dump") else k.__dict__ for k in keyframes]
