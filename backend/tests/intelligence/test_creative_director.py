"""Tests for the Creative Director."""

from app.intelligence.core.creative_director import CreativeDirector
from app.intelligence.schemas import CreativeDecision


class TestCreativeDirector:
    def test_plan_returns_creative_decision(self):
        director = CreativeDirector()
        decision = director.plan("cinematic video of a person at sunset")
        assert isinstance(decision, CreativeDecision)

    def test_composition(self):
        director = CreativeDirector()
        decision = director.plan("cinematic scene")
        assert "rule_of_thirds" in decision.composition

    def test_camera_movement(self):
        director = CreativeDirector()
        decision = director.plan("orbit around the subject")
        assert "movement" in decision.camera
        assert decision.camera["movement"] == "orbit"

    def test_lighting_warm(self):
        director = CreativeDirector()
        decision = director.plan("golden hour lighting")
        assert decision.lighting["temperature"] == "warm"

    def test_mood_detection(self):
        director = CreativeDirector()
        decision = director.plan("dramatic dark scene")
        assert decision.mood == "dramatic"

    def test_realism_levels(self):
        director = CreativeDirector()
        d1 = director.plan("stylized anime")
        assert d1.realism == "stylized"
        d2 = director.plan("cartoon illustration")
        assert d2.realism == "illustrative"
        d3 = director.plan("realistic photo")
        assert d3.realism == "photorealistic"

    def test_cinematic_intent(self):
        director = CreativeDirector()
        decision = director.plan("commercial advertisement")
        assert decision.cinematic_intent == "commercial"

    def test_environment_outdoor(self):
        director = CreativeDirector()
        decision = director.plan("outdoor city scene at night")
        assert decision.environment["type"] == "exterior"

    def test_rationale_present(self):
        director = CreativeDirector()
        decision = director.plan("cinematic video")
        assert len(decision.rationale) > 0

    def test_empty_prompt(self):
        director = CreativeDirector()
        decision = director.plan("")
        assert decision.mood == "dramatic"  # defaults to dramatic
