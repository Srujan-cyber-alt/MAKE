"""Tests for foley physics and reaction engine."""

import numpy as np
import pytest

from app.make_model.audio.foley_physics import FoleyPhysics, FoleyEvent, FoleyEventType
from app.make_model.audio.reaction_engine import ReactionEngine, ReactionSpec, ReactionType


class TestFoleyPhysics:
    def test_impact(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.IMPACT, duration=0.2)
        assert audio.size > 0
        assert np.max(np.abs(audio)) <= 1.0

    def test_friction(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.FRICTION, duration=0.3)
        assert audio.size > 0

    def test_scraping(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.SCRAPING, duration=0.3)
        assert audio.size > 0

    def test_collision(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.COLLISION, duration=0.2)
        assert audio.size > 0

    def test_movement(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.MOVEMENT, duration=0.3)
        assert audio.size > 0

    def test_deformation(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.DEFORMATION, duration=0.3)
        assert audio.size > 0

    def test_breakage(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.BREAKAGE, duration=0.3)
        assert audio.size > 0

    def test_compression(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.COMPRESSION, duration=0.3)
        assert audio.size > 0

    def test_stretching(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.STRETCHING, duration=0.3)
        assert audio.size > 0

    def test_liquid_displacement(self):
        physics = FoleyPhysics(sample_rate=16000)
        audio = physics.generate(FoleyEventType.LIQUID_DISPLACEMENT, duration=0.3)
        assert audio.size > 0

    def test_available_types(self):
        physics = FoleyPhysics()
        types = physics.available_types()
        assert len(types) == 10
        assert "impact" in types
        assert "liquid_displacement" in types

    def test_event_object(self):
        physics = FoleyPhysics(sample_rate=16000)
        event = FoleyEvent(event_type=FoleyEventType.IMPACT, duration=0.2, intensity=0.5, seed=42)
        audio = physics.synthesize(event)
        assert audio.size > 0

    def test_deterministic_seed(self):
        physics = FoleyPhysics(sample_rate=16000)
        a1 = physics.generate(FoleyEventType.IMPACT, duration=0.2, seed=42)
        a2 = physics.generate(FoleyEventType.IMPACT, duration=0.2, seed=42)
        assert np.allclose(a1, a2)


class TestReactionEngine:
    def test_breath(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.BREATH, duration=0.2)
        assert audio.size > 0

    def test_hesitation(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.HESITATION, duration=0.2)
        assert audio.size > 0

    def test_laugh(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.LAUGH, duration=0.5)
        assert audio.size > 0

    def test_sigh(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.SIGH, duration=0.2)
        assert audio.size > 0

    def test_gasp(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.GASP, duration=0.2)
        assert audio.size > 0

    def test_surprise(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.SURPRISE, duration=0.2)
        assert audio.size > 0

    def test_throat_clearing(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.THROAT_CLEARING, duration=0.2)
        assert audio.size > 0

    def test_quiet_acknowledgment(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.QUIET_ACKNOWLEDGMENT, duration=0.2)
        assert audio.size > 0

    def test_all_types(self):
        engine = ReactionEngine()
        for t in engine.available_types():
            audio = engine.generate(ReactionType(t), duration=0.1)
            assert audio.size > 0

    def test_spec_object(self):
        engine = ReactionEngine(sample_rate=16000)
        spec = ReactionSpec(reaction_type=ReactionType.LAUGH, duration=0.3, intensity=0.8, seed=7)
        audio = engine.synthesize(spec)
        assert audio.size > 0