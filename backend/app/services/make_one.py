"""
MakeOne — MAKE Video Unified Workflow Orchestrator for Phase 21.

One entry point for creating video from natural language.

Integrates:
- UniversalCommandEngine (intent parsing)
- MakeAutoMode (creative planning)
- GenesisEngine (generation quality)
- ModelLab (evidence-based routing)
- TimelineService (editing)
- AudioSystem, ColorLookEngine, CaptionSystem (finishing)
- ExportEngine (delivery)
"""

from typing import Optional, List, Dict, Any
from app.services.universal_command_engine import UniversalCommandEngine, ParsedCommand, CommandIntent
from app.services.make_auto_mode import MakeAutoMode
from app.services.genesis_engine import make_genesis
from app.services.model_leaderboard import model_leaderboard
from app.services.routing_benchmark import routing_benchmark
from app.services.production_engine import production_engine, ProductionGoal
from app.services.production_graph import production_graph, NodeStatus, NodeType
from app.services.timeline_service import TimelineService
from app.services.audio_system import AudioSystem
from app.services.color_look_engine import ColorLookEngine
from app.services.caption_system import CaptionSystem
from app.services.export_engine import ExportEngine
from app.services.capability_registry import CapabilityRegistry
from app.services.brand_dna import BrandDNA
from app.services.world_system import WorldSystem
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
from app.services.shot_generation_planner import shot_generation_planner
from app.services.continuity_engine import continuity_engine
from app.services.cinematic_quality_score import cinematic_quality_score
from app.services.generation_reality_layer import generation_reality_layer
from app.services.technical_validator import technical_validator
from app.services.artifact_detector import artifact_detector
from app.services.failure_classifier import failure_classifier
from app.services.repair_planner import repair_planner
from app.services.shot_intelligence import shot_intelligence
from app.services.budget_intelligence import budget_intelligence
from app.services.reference_intelligence import reference_intelligence
from app.services.best_result_selection import best_result_selector
from app.services.production_templates import production_templates
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class MakeOne:
    @staticmethod
    async def execute(
        user_id: str,
        project_id: str,
        prompt: str,
        source_asset_ids: Optional[List[str]] = None,
        brand_id: Optional[str] = None,
        world_id: Optional[str] = None,
        character_ids: Optional[List[str]] = None,
        product_ids: Optional[List[str]] = None,
        mode: str = "auto",
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        one_id = str(uuid.uuid4())
        logger.info(f"Starting MAKE ONE {one_id} for user {user_id}: {prompt}")

        parsed = UniversalCommandEngine.parse(prompt)
        plan = UniversalCommandEngine.to_execution_plan(parsed)

        if plan.get("needs_clarification"):
            return {
                "one_id": one_id,
                "status": "awaiting_clarification",
                "parsed_command": plan,
                "clarification_questions": plan.get("clarification_questions", []),
            }

        capabilities = await CapabilityRegistry.get_all_capabilities()
        brand = None
        if brand_id:
            brand = await BrandDNA.get_brand_dna(brand_id)
        world = None
        if world_id:
            world = await WorldSystem.get_world(world_id)

        context = {
            "user_id": user_id,
            "project_id": project_id,
            "source_asset_ids": source_asset_ids or [],
            "brand": brand,
            "world": world,
            "character_ids": character_ids or [],
            "product_ids": product_ids or [],
            "capabilities": capabilities,
            "mode": mode,
            "template_id": template_id,
        }

        try:
            result = await MakeOne._run_workflow(plan, context)
            result["one_id"] = one_id
            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat()
            return result
        except Exception as e:
            logger.error(f"MAKE ONE failed: {e}")
            return {
                "one_id": one_id,
                "status": "failed",
                "error": str(e),
            }

    @staticmethod
    async def _run_workflow(plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        intent = plan.get("intent", "unknown")
        results = []

        if intent in ("generate_video", "edit_video", "extend_video", "create_variants"):
            auto_result = await MakeAutoMode.execute(
                user_id=context.get("user_id", ""),
                project_id=context.get("project_id", ""),
                prompt=plan.get("original_text", plan.get("parameters", {}).get("original_text", "")),
                source_asset_ids=context.get("source_asset_ids"),
                brand_id=context.get("brand_id"),
                world_id=context.get("world_id"),
                character_ids=context.get("character_ids"),
                product_ids=context.get("product_ids"),
                approval_mode=context.get("mode", "auto"),
            )
            results.append(auto_result)

        return {
            "intent": intent,
            "steps_executed": len(results),
            "results": results,
        }


make_one = MakeOne()
