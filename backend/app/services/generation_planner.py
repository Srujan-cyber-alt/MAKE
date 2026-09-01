from typing import List, Dict, Any, Optional
from app.schemas.director import DirectorPlan, ScenePlan, ShotPlan, GenerationRequirement
from app.models.models import JobType


class GenerationPlanner:
    def plan_generation(
        self,
        plan: DirectorPlan,
        shot_ids: List[str] = None,
        scene_ids: List[str] = None,
        preferences: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        preferences = preferences or {}
        jobs = []

        for scene in plan.scenes:
            if scene_ids and scene.id not in scene_ids:
                continue

            for shot in scene.shots:
                if shot_ids and shot.id not in shot_ids:
                    continue

                if shot.generation and shot.generation.method:
                    job = self._create_job_plan(plan, scene, shot, preferences)
                    jobs.append(job)

        return jobs

    def _create_job_plan(
        self,
        plan: DirectorPlan,
        scene: ScenePlan,
        shot: ShotPlan,
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        method = shot.generation.method if shot.generation else "TEXT_TO_VIDEO"
        job_type_map = {
            "TEXT_TO_VIDEO": JobType.TEXT_TO_VIDEO,
            "IMAGE_TO_VIDEO": JobType.IMAGE_TO_VIDEO,
            "VIDEO_TO_VIDEO": JobType.VIDEO_TO_VIDEO,
            "REFERENCE_GENERATION": JobType.TEXT_TO_VIDEO,
            "GENERATIVE_TRANSFORMATION": JobType.TEXT_TO_VIDEO,
        }

        return {
            "plan_id": plan.id,
            "scene_id": scene.id,
            "shot_id": shot.id,
            "job_type": job_type_map.get(method, JobType.TEXT_TO_VIDEO),
            "prompt": shot.description or plan.objective,
            "negative_prompt": None,
            "duration_seconds": shot.duration_seconds,
            "aspect_ratio": plan.aspect_ratio,
            "resolution": plan.resolution,
            "width": self._parse_resolution_width(plan.resolution),
            "height": self._parse_resolution_height(plan.resolution),
            "fps": 24,
            "references": shot.references or [],
            "characters": shot.characters or [],
            "products": shot.products or [],
            "locations": shot.locations or [],
            "generation_method": method,
            "required_capabilities": shot.generation.required_capabilities if shot.generation else [],
            "parameters": shot.generation.parameters if shot.generation else {},
            "preferences": preferences,
            "status": "planned",
        }

    def _parse_resolution_width(self, resolution: str) -> Optional[int]:
        if not resolution:
            return None
        if "x" in resolution.lower():
            parts = resolution.lower().split("x")
            try:
                return int(parts[0])
            except (ValueError, IndexError):
                pass
        if resolution == "1080p":
            return 1920
        if resolution == "720p":
            return 1280
        if resolution == "4k":
            return 3840
        return None

    def _parse_resolution_height(self, resolution: str) -> Optional[int]:
        if not resolution:
            return None
        if "x" in resolution.lower():
            parts = resolution.lower().split("x")
            try:
                return int(parts[1])
            except (ValueError, IndexError):
                pass
        if resolution == "1080p":
            return 1080
        if resolution == "720p":
            return 720
        if resolution == "4k":
            return 2160
        return None
