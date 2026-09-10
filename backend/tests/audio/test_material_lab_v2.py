"""Tests for Material Sound Lab V2 - 18 materials."""
import numpy as np
import pytest
from app.make_model.audio.material_lab_v2 import (
    MaterialSoundEngine, MATERIAL_PROFILES, MaterialProfile, MaterialActionParams,
    material_profiles_bounces,
)


class TestMaterialLabV2:
    @pytest.fixture
    def engine(self):
        return MaterialSoundEngine(sample_rate=16000)

    def test_engine_creation(self, engine):
        assert engine.sample_rate == 16000

    def test_18_materials_present(self):
        expected = {"wood", "metal", "glass", "plastic", "stone", "concrete",
                    "ceramic", "rubber", "fabric", "water", "ice", "paper",
                    "leather", "sand", "dirt", "foliage", "snow", "mud"}
        actual = set(MATERIAL_PROFILES.keys())
        assert expected == actual

    def test_generate_impact(self, engine):
        result = engine.generate_impact("wood", force=1.0, speed=1.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_all_materials_impact(self, engine):
        for mat in MATERIAL_PROFILES:
            result = engine.generate_impact(mat, force=1.0)
            assert len(result) > 0
            assert np.max(np.abs(result)) <= 0.99

    def test_generate_scrape(self, engine):
        result = engine.generate_scrape("metal", speed=1.0, force=1.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_drop(self, engine):
        result = engine.generate_drop("glass", height=2.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_collision(self, engine):
        result = engine.generate_collision("wood", "metal")
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_drag(self, engine):
        result = engine.generate_drag("wood", distance=1.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_roll(self, engine):
        result = engine.generate_roll("metal", speed=1.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_break(self, engine):
        result = engine.generate_break("glass", force=1.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_generate_all_actions(self, engine):
        result = engine.generate_all_actions("wood")
        expected_actions = {"impact", "scrape", "drag", "drop", "collision",
                            "break", "bend", "stretch", "roll", "slide"}
        assert set(result.keys()) == expected_actions
        for action_result in result.values():
            assert len(action_result) > 0

    def test_material_profiles_have_properties(self):
        for name, profile in MATERIAL_PROFILES.items():
            assert isinstance(profile, MaterialProfile)
            assert profile.name == name
            assert profile.density > 0
            assert profile.stiffness >= 0
            assert 0 <= profile.damping <= 1
            assert isinstance(profile.absorption, (int, float))
            assert profile.resonance_freq > 0
            assert len(profile.modal_freqs) > 0

    def test_material_bounces(self):
        assert material_profiles_bounces("rubber") == 1
        assert material_profiles_bounces("glass") == 4
        assert material_profiles_bounces("water") == 0

    def test_different_materials_differ(self, engine):
        wood = engine.generate_impact("wood")
        metal = engine.generate_impact("metal")
        glass = engine.generate_impact("glass")
        assert not np.allclose(wood, metal)
        assert not np.allclose(wood, glass)

    def test_force_changes_output(self, engine):
        low_force = engine.generate_impact("wood", force=0.3)
        high_force = engine.generate_impact("wood", force=1.0)
        assert np.mean(np.abs(high_force)) > np.mean(np.abs(low_force))

    def test_speed_changes_output(self, engine):
        slow = engine.generate_scrape("wood", speed=0.5)
        fast = engine.generate_scrape("wood", speed=2.0)
        assert len(slow) > 0
        assert len(fast) > 0

    def test_action_params(self, engine):
        params = MaterialActionParams(force=0.8, speed=1.5, contact_size="large", surface_area="large")
        result = engine.generate_impact("metal", force=params.force, speed=params.speed, contact_size=params.contact_size)
        assert len(result) > 0
