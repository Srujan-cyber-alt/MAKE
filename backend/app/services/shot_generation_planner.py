"""
Shot Generation Planner for MAKE AI Video Phase 18.

Creates per-shot generation plans with model routing through Universal Model Engine.
"""

from typing import Optional, List, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class ShotGenerationPlanner:
    @staticmethod
    def create_shot_plan(shot: Dict[str, Any], production_context: Dict[str, Any]) -> Dict[str, Any]:
        shot_id = shot.get("shot_id", str(uuid.uuid4()))
        scene_id = shot.get("scene_id")
        brief = production_context.get("brief", {})

        input_mode = ShotGenerationPlanner._determine_input_mode(shot, brief)
        model_requirements = ShotGenerationPlanner._determine_model_requirements(shot, brief)
        prompt = ShotGenerationPlanner._compile_shot_prompt(shot, production_context)
        negative_prompt = ShotGenerationPlanner._compile_negative_prompt(shot, brief)
        references = ShotGenerationPlanner._collect_references(shot, production_context)

        plan = {
            "shot_id": shot_id,
            "scene_id": scene_id,
            "input_mode": input_mode,
            "model_requirements": model_requirements,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "references": references,
            "duration_seconds": shot.get("duration_seconds", 5.0),
            "resolution": brief.get("resolution", "1920x1080"),
            "aspect_ratio": brief.get("aspect_ratio", "16:9"),
            "camera": shot.get("camera", {}),
            "motion": shot.get("motion", {}),
            "identity_constraints": production_context.get("identity_constraints", []),
            "product_constraints": production_context.get("product_constraints", []),
            "world_constraints": production_context.get("world_constraints", []),
            "quality_requirements": {
                "min_quality_score": 0.7,
                "require_temporal_consistency": True,
                "require_identity_lock": "person" in (shot.get("description", "").lower()),
            },
            "status": "planned",
        }
        return plan

    @staticmethod
    def _determine_input_mode(shot: Dict[str, Any], brief: Dict[str, Any]) -> str:
        if shot.get("first_frame") and shot.get("last_frame"):
            return "first_last_frame"
        elif shot.get("reference_images"):
            return "reference_to_video"
        elif shot.get("source_asset_id"):
            return "video_to_video"
        return "text_to_video"

    @staticmethod
    def _determine_model_requirements(shot: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
        reqs = {
            "required_capabilities": ["text_to_video"],
            "min_duration": shot.get("duration_seconds", 5.0),
            "max_duration": shot.get("duration_seconds", 5.0),
            "aspect_ratio": brief.get("aspect_ratio", "16:9"),
            "resolution": brief.get("resolution", "1920x1080"),
        }
        if shot.get("camera", {}).get("movement") and shot["camera"]["movement"] != "static":
            reqs["required_capabilities"].append("camera_control")
        if shot.get("motion"):
            reqs["required_capabilities"].append("motion_generation")
        if "person" in shot.get("description", "").lower():
            reqs["required_capabilities"].append("character_consistency")
        return reqs

    @staticmethod
    def _compile_shot_prompt(shot: Dict[str, Any], context: Dict[str, Any]) -> str:
        parts = []
        if shot.get("description"):
            parts.append(shot["description"])
        camera = shot.get("camera") or {}
        if camera.get("movement") and camera["movement"] != "static":
            parts.append(f"camera: {camera['movement']}")
        if camera.get("lens"):
            parts.append(f"lens: {camera['lens']}")
        if shot.get("lighting"):
            parts.append(f"lighting: {shot['lighting']}")
        if shot.get("motion"):
            parts.append(f"motion: {shot['motion']}")
        world = context.get("world") or {}
        if world.get("lighting"):
            parts.append(f"environment lighting: {world['lighting']}")
        if world.get("weather"):
            parts.append(f"weather: {world['weather']}")
        if world.get("time"):
            parts.append(f"time: {world['time']}")
        brief = context.get("brief") or {}
        if brief.get("tone"):
            parts.append(f"tone: {brief['tone']}")
        if brief.get("style"):
            parts.append(f"style: {brief['style']}")
        return ". ".join(parts) if parts else shot.get("description", "")

    @staticmethod
    def _compile_negative_prompt(shot: Dict[str, Any], brief: Dict[str, Any]) -> str:
        negatives = ["blurry", "low quality", "distorted", "watermark", "text"]
        if shot.get("identity_constraints"):
            negatives.append("identity change")
        if shot.get("product_constraints"):
            negatives.append("product deformation")
        return ", ".join(negatives)

    @staticmethod
    def _collect_references(shot: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        refs = []
        if shot.get("reference_images"):
            refs.extend(shot["reference_images"])
        if context.get("character_ids"):
            refs.extend(context["character_ids"])
        if context.get("product_ids"):
            refs.extend(context["product_ids"])
        if context.get("world") and context["world"].get("reference_images"):
            refs.extend(context["world"]["reference_images"])
        return list(set(refs))


shot_generation_planner = ShotGenerationPlanner()
