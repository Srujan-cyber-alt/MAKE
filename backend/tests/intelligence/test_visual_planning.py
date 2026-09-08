"""Tests for Visual Planning Engine."""

import pytest

from app.intelligence.core.visual_planning import VisualPlanningEngine
from app.intelligence.core.creative_director import CreativeDirector
from app.intelligence.schemas import CreativeDecision, VisualPlan, ScenePlan


class TestVisualPlanning:
    def test_plan_scene(self):
        director = CreativeDirector()
        planner = VisualPlanningEngine()
        decision = director.plan("cinematic video of a person")
        scene = planner.plan_scene("cinematic video of a person", decision)
        assert isinstance(scene, ScenePlan)
        assert len(scene.shots) > 0
        assert scene.creative_decision is not None

    def test_plan_visual(self):
        director = CreativeDirector()
        planner = VisualPlanningEngine()
        decision = director.plan("cinematic video of a person walking")
        plan = planner.plan_visual("cinematic video of a person walking", decision)
        assert isinstance(plan, VisualPlan)
        assert len(plan.scenes) >= 1

    def test_shot_has_duration(self):
        director = CreativeDirector()
        planner = VisualPlanningEngine()
        decision = director.plan("cinematic video")
        scene = planner.plan_scene("cinematic video", decision, max_duration_seconds=10.0, num_shots=4)
        for shot in scene.shots:
            assert shot.duration_seconds > 0

    def test_shot_has_camera_movement(self):
        planner = VisualPlanningEngine()
        decision = CreativeDecision(mood="dramatic", realism="photorealistic", cinematic_intent="cinematic")
        scene = planner.plan_scene("test", decision)
        assert len(scene.shots[0].camera_movement) > 0

    def test_shot_requirements(self):
        from app.intelligence.schemas import Intent, IntentCategory
        planner = VisualPlanningEngine()
        decision = CreativeDecision(mood="dramatic", realism="photorealistic", cinematic_intent="cinematic")
        intent = Intent(category=IntentCategory.CREATIVE, raw_request="create video")
        scene = planner.plan_scene("test", decision, intent=intent)
        assert len(scene.shots) > 0

    def test_num_shots_clamped(self):
        planner = VisualPlanningEngine()
        decision = CreativeDecision(mood="dramatic", realism="photorealistic", cinematic_intent="cinematic")
        scene = planner.plan_scene("test", decision, num_shots=20)
        assert len(scene.shots) <= 8
