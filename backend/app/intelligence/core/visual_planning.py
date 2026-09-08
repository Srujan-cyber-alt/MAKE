"""Visual Planning Engine — breaks creative briefs into shot/scene plans.

Works with CreativeDirector output to produce concrete shot lists and
scene breakdowns. Plans, not fabricates.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.intelligence.schemas import (
    CreativeDecision, VisualPlan, ScenePlan, ShotPlan, Intent,
)


class VisualPlanningEngine:
    """Produces structured visual shot/scene plans from creative decisions."""

    CAMERA_MOVEMENTS = ["static", "pan", "tilt", "dolly", "orbit", "handheld", "crane"]
    COMPOSITION_FRAMINGS = ["wide", "medium", "close_up", "extreme_close_up"]

    def __init__(self) -> None:
        pass

    def plan_scene(
        self,
        prompt: str,
        creative_decision: CreativeDecision,
        intent: Optional[Intent] = None,
        max_duration_seconds: float = 10.0,
        num_shots: int = 3,
    ) -> ScenePlan:
        """Generate a single scene plan from a creative decision."""
        num_shots = min(max(num_shots, 1), 8)
        duration_per_shot = max_duration_seconds / num_shots

        camera_move = creative_decision.camera.get("movement", "static")
        shots: List[ShotPlan] = []
        for i in range(num_shots):
            shot = ShotPlan(
                shot_number=i + 1,
                description=f"Shot {i + 1}: {camera_move} shot of {prompt}",
                duration_seconds=round(duration_per_shot, 2),
                camera_movement=camera_move if i > 0 else "static",
                composition={
                    "rule_of_thirds": creative_decision.composition.get("rule_of_thirds", True),
                    "depth_of_field": creative_decision.composition.get("depth_of_field", "shallow"),
                },
                creative_notes=self._shot_notes(creative_decision, i),
                requirements=self._shot_requirements(intent, i),
            )
            shots.append(shot)

        return ScenePlan(
            scene_number=1,
            description=prompt,
            shots=shots,
            creative_decision=creative_decision,
        )

    def plan_visual(
        self,
        prompt: str,
        creative_decision: CreativeDecision,
        intent: Optional[Intent] = None,
        max_duration_seconds: float = 10.0,
        num_scenes: int = 1,
    ) -> VisualPlan:
        """Generate a full visual plan with multiple scenes."""
        scenes: List[ScenePlan] = []
        for i in range(max(num_scenes, 1)):
            scene = self.plan_scene(
                prompt,
                creative_decision,
                intent,
                max_duration_seconds / num_scenes,
                num_shots=3,
            )
            scene.scene_number = i + 1
            scenes.append(scene)

        return VisualPlan(
            scenes=scenes,
            overall_notes=[
                f"Visual plan for: {prompt}",
                f"Cinematic intent: {creative_decision.cinematic_intent}",
                f"Mood: {creative_decision.mood}",
                f"Realism: {creative_decision.realism}",
            ],
        )

    def _shot_notes(self, decision: CreativeDecision, index: int) -> List[str]:
        notes: List[str] = []
        if decision.mood:
            notes.append(f"Mood reference: {decision.mood}")
        if decision.lighting.get("temperature"):
            notes.append(f"Lighting: {decision.lighting['temperature']}")
        if index == 0:
            notes.append("Opening shot establishes the scene")
        elif index == 1:
            notes.append("Secondary angle provides variety")
        else:
            notes.append("Closing/reverse angle for rhythm")
        return notes

    def _shot_requirements(self, intent: Optional[Intent], index: int) -> List[str]:
        reqs: List[str] = []
        if intent:
            if "make_video" in intent.required_capabilities:
                reqs.append("video_output")
            if "make_image" in intent.required_capabilities:
                reqs.append("image_output")
        if index == 0:
            reqs.append("establishing_shot")
        return reqs
