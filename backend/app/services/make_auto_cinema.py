"""
MAKE AUTO CINEMA for MAKE AI Video Phase 18.

Full end-to-end cinema production from creative brief to final master.
"""

from typing import Optional, List, Dict, Any
from app.services.production_engine import production_engine, ProductionGoal, ProductionStatus
from app.services.production_graph import production_graph, NodeStatus, NodeType
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
from app.services.shot_generation_planner import shot_generation_planner
from app.services.continuity_engine import continuity_engine
from app.services.cinematic_quality_score import cinematic_quality_score
from app.services.production_templates import production_templates
from app.services.universal_model_registry import UniversalModelRegistry
from app.services.model_router_4 import model_router_4, RoutingMode
from app.services.budget_controller import budget_controller
from app.services.timeline_service import TimelineService
from app.services.audio_system import AudioSystem
from app.services.color_look_engine import ColorLookEngine
from app.services.caption_system import CaptionSystem
from app.services.export_engine import ExportEngine
from app.services.quality_control import QualityControl
from app.services.versioning import VersionWorkflow
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class MakeAutoCinema:
    @staticmethod
    async def execute(
        user_id: str,
        project_id: str,
        brief: Dict[str, Any],
        goal: str = ProductionGoal.COMMERCIAL,
        mode: str = "balanced",
        template_id: Optional[str] = None,
        world_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        character_ids: List[str] = None,
        product_ids: List[str] = None,
    ) -> Dict[str, Any]:
        auto_id = str(uuid.uuid4())
        logger.info(f"Starting MAKE AUTO CINEMA {auto_id} for user {user_id}: {brief.get('objective', '')}")

        production = await production_engine.create_production(project_id, user_id, brief, goal)
        graph = production_graph.create_graph(production["production_id"])

        production_graph.add_node(graph, NodeType.BRIEF, f"brief_{production['production_id']}", {"brief": brief})

        context = {
            "user_id": user_id,
            "project_id": project_id,
            "brief": brief,
            "goal": goal,
            "world_id": world_id,
            "brand_id": brand_id,
            "character_ids": character_ids or [],
            "product_ids": product_ids or [],
            "mode": mode,
        }

        try:
            production = await MakeAutoCinema._run_pipeline(production, graph, context)
            production["auto_id"] = auto_id
            production["status"] = ProductionStatus.COMPLETED
            production["completed_at"] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"MAKE AUTO CINEMA failed: {e}")
            production["status"] = ProductionStatus.FAILED
            production["error"] = str(e)

        return production

    @staticmethod
    async def _run_pipeline(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        production = await MakeAutoCinema._stage_story(production, graph, context)
        production = await MakeAutoCinema._stage_storyboard(production, graph, context)
        production = await MakeAutoCinema._stage_shot_planning(production, graph, context)
        production = await MakeAutoCinema._stage_generation_planning(production, graph, context)
        production = await MakeAutoCinema._stage_continuity(production, graph, context)
        production = await MakeAutoCinema._stage_quality(production, graph)
        production = await MakeAutoCinema._stage_assembly(production, graph, context)
        return production

    @staticmethod
    async def _stage_story(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        brief = context.get("brief", {})
        creative_brief = CreativeBrief(
            objective=brief.get("objective", ""),
            audience=brief.get("audience"),
            platform=brief.get("platform"),
            genre=brief.get("genre"),
            tone=brief.get("tone"),
            duration_seconds=brief.get("duration_seconds", 30),
            aspect_ratio=brief.get("aspect_ratio", "16:9"),
            characters=[],
            products=[],
            locations=[],
            brand_dna=None,
            reference_assets=[],
            user_id=context.get("user_id"),
            project_id=context.get("project_id"),
        )
        creative_plan = CreativeDirector.create_creative_director(creative_brief, ApprovalMode.AUTO)
        script = ScriptEngine.generate_script(
            creative_plan=creative_plan,
            genre=creative_plan.get("genre", "commercial"),
            tone=creative_plan.get("tone", "cinematic"),
            duration_seconds=brief.get("duration_seconds", 30),
        )

        story_node_id = f"story_{production['production_id']}"
        production_graph.add_node(graph, NodeType.STORY, story_node_id, {"creative_plan": creative_plan, "script": script})
        production_graph.add_edge(graph, f"brief_{production['production_id']}", story_node_id)
        production_graph.update_node_status(graph, story_node_id, NodeStatus.COMPLETED)

        production["story"] = creative_plan
        production["script"] = script
        return production

    @staticmethod
    async def _stage_storyboard(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        creative_plan = production.get("story") or {}
        storyboard = StoryboardEngine.generate_storyboard(creative_plan, context.get("project_id"))
        storyboard_node_id = f"storyboard_{production['production_id']}"
        production_graph.add_node(graph, NodeType.SCENE, storyboard_node_id, {"storyboard": storyboard})
        production_graph.add_edge(graph, f"story_{production['production_id']}", storyboard_node_id)
        production_graph.update_node_status(graph, storyboard_node_id, NodeStatus.COMPLETED)
        production["storyboard"] = storyboard
        return production

    @staticmethod
    async def _stage_shot_planning(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = production.get("storyboard") or {}
        scenes = storyboard.get("scenes", [])
        shot_plans = []
        for scene in scenes:
            for shot in scene.get("shots", []):
                plan = shot_generation_planner.create_shot_plan(shot, {
                    "brief": context.get("brief", {}),
                    "world": context.get("world"),
                    "character_ids": context.get("character_ids", []),
                    "product_ids": context.get("product_ids", []),
                    "identity_constraints": [],
                    "product_constraints": [],
                    "world_constraints": [],
                })
                shot_plans.append(plan)
                shot_node_id = f"shot_{plan['shot_id']}"
                production_graph.add_node(graph, NodeType.SHOT, shot_node_id, {"plan": plan})
                production_graph.add_edge(graph, f"storyboard_{production['production_id']}", shot_node_id)
                production_graph.update_node_status(graph, shot_node_id, NodeStatus.PLANNED)
        production["shot_plans"] = shot_plans
        production["shots"] = shot_plans
        return production

    @staticmethod
    async def _stage_generation_planning(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        shot_plans = production.get("shot_plans", [])
        for plan in shot_plans:
            model_req = plan.get("model_requirements", {})
            routing = model_router_4.select_model(
                required_capabilities=model_req.get("required_capabilities", []),
                duration_seconds=plan.get("duration_seconds", 5.0),
                aspect_ratio=plan.get("aspect_ratio", "16:9"),
                mode=RoutingMode.AUTO,
            )
            plan["selected_model"] = routing.get("selected_model")
            plan["selected_provider"] = routing.get("selected_provider")
            plan["generation_estimated_cost"] = routing.get("estimated_cost")
            plan["status"] = "ready_for_generation"
            gen_node_id = f"generation_{plan['shot_id']}"
            production_graph.add_node(graph, NodeType.GENERATION, gen_node_id, {"plan": plan})
            shot_node_id = f"shot_{plan['shot_id']}"
            production_graph.add_edge(graph, shot_node_id, gen_node_id)
            production_graph.update_node_status(graph, gen_node_id, NodeStatus.READY)
        return production

    @staticmethod
    async def _stage_continuity(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        shots = production.get("shots", [])
        continuity_report = continuity_engine.validate_shot_continuity(shots, {})
        continuity_node_id = f"continuity_{production['production_id']}"
        production_graph.add_node(graph, NodeType.SCENE, continuity_node_id, {"report": continuity_report})
        for plan in shots:
            shot_node_id = f"shot_{plan.get('shot_id')}"
            production_graph.add_edge(graph, shot_node_id, continuity_node_id)
        production_graph.update_node_status(graph, continuity_node_id, NodeStatus.COMPLETED)
        production["continuity_report"] = continuity_report
        return production

    @staticmethod
    async def _stage_quality(production: Dict[str, Any], graph: Dict[str, Any]) -> Dict[str, Any]:
        quality_report = cinematic_quality_score.score_production(production)
        qc_node_id = f"qc_{production['production_id']}"
        production_graph.add_node(graph, NodeType.QC, qc_node_id, {"report": quality_report})
        production_graph.update_node_status(graph, qc_node_id, NodeStatus.COMPLETED)
        production["qc_report"] = quality_report
        return production

    @staticmethod
    async def _stage_assembly(production: Dict[str, Any], graph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        timeline = TimelineService.create_timeline(context.get("project_id"), context.get("user_id"), production.get("brief", {}).get("duration_seconds", 30))
        master_node_id = f"master_{production['production_id']}"
        production_graph.add_node(graph, NodeType.MASTER, master_node_id, {"timeline": timeline})
        production_graph.update_node_status(graph, master_node_id, NodeStatus.COMPLETED)
        production["master_output"] = timeline
        return production


make_auto_cinema = MakeAutoCinema()
