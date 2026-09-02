"""
Studio Orchestrator Service for MAKE AI Video.

Routes unified Studio commands to existing engines.
Does NOT duplicate existing functionality.
"""

from typing import Optional, List, Dict, Any
from app.services.universal_command_engine import UniversalCommandEngine, ParsedCommand, CommandIntent
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode, Genre, Tone
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
from app.services.variant_engine import VariantEngine
from app.services.media_understanding import MediaUnderstanding
from app.services.smart_model_router import SmartModelRouterV3
from app.services.image_to_video_engine import ImageToVideoEngine
from app.services.video_to_video_engine import VideoToVideoEngine
from app.services.video_extension_engine import VideoExtensionEngine
from app.services.character_performance_engine import CharacterPerformanceEngine
from app.services.audio_system import AudioSystem
from app.services.caption_system import CaptionSystem
from app.services.color_look_engine import ColorLookEngine
from app.services.quality_control import QualityControl
from app.services.intelligent_shot_repair import IntelligentShotRepair
from app.services.timeline_service import TimelineService
from app.services.export_engine import ExportEngine
from app.services.brand_dna import BrandDNA
from app.services.world_system import WorldSystem
from app.services.capability_registry import CapabilityRegistry
from app.services.asset_intelligence import AssetIntelligence
from app.services.make_auto_mode import MakeAutoMode
from app.services.transformation_engine import TransformationEngine
from app.services.generation_engine import GenerationEngine
from app.services.director import DirectorService
import uuid
import logging

logger = logging.getLogger(__name__)


class CreationMode:
    CREATE = "create"
    EDIT = "edit"
    TRANSFORM = "transform"
    ANIMATE = "animate"
    EXTEND = "extend"
    REMIX = "remix"
    AUTO = "auto"


class StudioOrchestrator:
    @staticmethod
    async def route_command(
        command: str,
        project_id: str,
        user_id: str,
        mode: str = CreationMode.AUTO,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = context or {}
        parsed = UniversalCommandEngine.parse(command, context)
        execution_plan = UniversalCommandEngine.to_execution_plan(parsed)

        if execution_plan.get("needs_clarification"):
            return {
                "status": "awaiting_clarification",
                "plan": execution_plan,
                "clarification_questions": execution_plan.get("clarification_questions", []),
            }

        intent = execution_plan.get("intent", "unknown")
        effective_mode = StudioOrchestrator._determine_mode(mode, intent)

        if effective_mode == CreationMode.AUTO:
            return await StudioOrchestrator._execute_auto(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.CREATE:
            return await StudioOrchestrator._execute_create(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.EDIT:
            return await StudioOrchestrator._execute_edit(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.TRANSFORM:
            return await StudioOrchestrator._execute_transform(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.ANIMATE:
            return await StudioOrchestrator._execute_animate(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.EXTEND:
            return await StudioOrchestrator._execute_extend(execution_plan, project_id, user_id, context)
        elif effective_mode == CreationMode.REMIX:
            return await StudioOrchestrator._execute_remix(execution_plan, project_id, user_id, context)
        else:
            return await StudioOrchestrator._execute_auto(execution_plan, project_id, user_id, context)

    @staticmethod
    def _determine_mode(requested_mode: str, intent: str) -> str:
        if requested_mode != CreationMode.AUTO:
            return requested_mode
        mode_map = {
            "generate_video": CreationMode.CREATE,
            "edit_video": CreationMode.EDIT,
            "extend_video": CreationMode.EXTEND,
            "create_variants": CreationMode.REMIX,
            "replace_background": CreationMode.TRANSFORM,
            "change_clothing": CreationMode.TRANSFORM,
            "remove_object": CreationMode.EDIT,
            "add_vfx": CreationMode.EDIT,
            "change_camera": CreationMode.EDIT,
            "change_motion": CreationMode.ANIMATE,
            "apply_color": CreationMode.EDIT,
        }
        return mode_map.get(intent, CreationMode.AUTO)

    @staticmethod
    async def _execute_auto(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result = await MakeAutoMode.execute(
            user_id=user_id,
            project_id=project_id,
            prompt=plan.get("original_text", ""),
            source_asset_ids=context.get("source_asset_ids"),
            brand_id=context.get("brand_id"),
            world_id=context.get("world_id"),
            character_ids=context.get("character_ids"),
            product_ids=context.get("product_ids"),
            approval_mode="auto",
        )
        result["mode"] = CreationMode.AUTO
        return result

    @staticmethod
    async def _execute_create(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        brief = CreativeBrief(
            objective=plan.get("original_text", "Generate video"),
            duration_seconds=plan.get("parameters", {}).get("duration_seconds", 30),
            aspect_ratio=plan.get("parameters", {}).get("aspect_ratio", "16:9"),
            characters=context.get("character_ids", []),
            products=context.get("product_ids", []),
            locations=[],
            brand_dna=None,
            reference_assets=context.get("source_asset_ids", []),
            user_id=user_id,
        )
        creative_plan = CreativeDirector.create_creative_director(brief, ApprovalMode.AUTO)
        storyboard = StoryboardEngine.generate_storyboard(creative_plan)
        script = ScriptEngine.generate_script(
            creative_plan=creative_plan,
            genre=creative_plan.get("genre", "commercial"),
            tone=creative_plan.get("tone", "cinematic"),
            duration_seconds=plan.get("parameters", {}).get("duration_seconds", 30),
        )
        return {
            "mode": CreationMode.CREATE,
            "status": "planned",
            "creative_plan": creative_plan,
            "storyboard": storyboard,
            "script": script,
        }

    @staticmethod
    async def _execute_edit(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source_asset_id = context.get("source_asset_id") or (context.get("source_asset_ids") or [""])[0]
        if not source_asset_id:
            return {"mode": CreationMode.EDIT, "status": "error", "error": "No source asset provided for editing"}

        result = await VideoToVideoEngine.transform_video(
            source_asset_id=source_asset_id,
            project_id=project_id,
            user_id=user_id,
            prompt=plan.get("original_text", ""),
            preserve_person="person" in plan.get("original_text", "").lower(),
            preserve_product="product" in plan.get("original_text", "").lower(),
        )
        result["mode"] = CreationMode.EDIT
        return result

    @staticmethod
    async def _execute_transform(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source_asset_id = context.get("source_asset_id") or (context.get("source_asset_ids") or [""])[0]
        if not source_asset_id:
            return {"mode": CreationMode.TRANSFORM, "status": "error", "error": "No source asset provided for transformation"}

        from app.schemas.transformation import TransformationRequest, TransformationOperation
        request = TransformationRequest(
            project_id=project_id,
            source_asset_id=source_asset_id,
            prompt=plan.get("original_text", ""),
            operations=[TransformationOperation(type="style_transfer", target={"type": "full", "description": plan.get("original_text", "")})],
            preserve_identity="person" in plan.get("original_text", "").lower(),
        )
        engine = TransformationEngine(
            provider_registry=__import__("app.providers.registry", fromlist=["get_provider_registry"]).get_provider_registry(),
            db_session_factory=__import__("app.core.database", fromlist=["async_session_maker"]).async_session_maker,
        )
        result = await engine.execute_transformation(request, user_id)
        result["mode"] = CreationMode.TRANSFORM
        return result

    @staticmethod
    async def _execute_animate(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source_asset_id = context.get("source_asset_id") or (context.get("source_asset_ids") or [""])[0]
        if not source_asset_id:
            return {"mode": CreationMode.ANIMATE, "status": "error", "error": "No source asset provided for animation"}

        result = await ImageToVideoEngine.create_video_from_image(
            source_asset_id=source_asset_id,
            project_id=project_id,
            user_id=user_id,
            prompt=plan.get("original_text", ""),
            duration_seconds=plan.get("parameters", {}).get("duration_seconds", 5.0),
        )
        result["mode"] = CreationMode.ANIMATE
        return result

    @staticmethod
    async def _execute_extend(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source_asset_id = context.get("source_asset_id") or (context.get("source_asset_ids") or [""])[0]
        if not source_asset_id:
            return {"mode": CreationMode.EXTEND, "status": "error", "error": "No source asset provided for extension"}

        params = plan.get("parameters", {})
        result = await VideoExtensionEngine.extend_video(
            source_asset_id=source_asset_id,
            project_id=project_id,
            user_id=user_id,
            extend_position=params.get("temporal_range", {}).get("position", "end"),
            extend_duration_seconds=params.get("duration_seconds", 5.0),
        )
        result["mode"] = CreationMode.EXTEND
        return result

    @staticmethod
    async def _execute_remix(plan: Dict[str, Any], project_id: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source_asset_id = context.get("source_asset_id") or (context.get("source_asset_ids") or [""])[0]
        if not source_asset_id:
            return {"mode": CreationMode.REMIX, "status": "error", "error": "No source asset provided for remix"}

        brief = CreativeBrief(
            objective=f"Remix: {plan.get('original_text', '')}",
            duration_seconds=plan.get("parameters", {}).get("duration_seconds", 30),
            aspect_ratio=plan.get("parameters", {}).get("aspect_ratio", "16:9"),
            characters=context.get("character_ids", []),
            products=context.get("product_ids", []),
            locations=[],
            brand_dna=None,
            reference_assets=[source_asset_id],
            user_id=user_id,
        )
        creative_plan = CreativeDirector.create_creative_director(brief, ApprovalMode.AUTO)
        variants = VariantEngine.generate_variants(creative_plan, num_variants=plan.get("parameters", {}).get("count", 3))
        variants["mode"] = CreationMode.REMIX
        return variants
