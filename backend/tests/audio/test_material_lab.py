"""Tests for Material Sound Lab."""
from __future__ import annotations
import pytest
from app.make_model.audio.material_lab import MaterialSoundLab, MaterialProfile

class TestMaterialLab:
    @pytest.fixture
    def lab(self):
        return MaterialSoundLab()

    def test_preset_count(self, lab):
        assert len(lab.list_materials()) >= 14

    def test_wood_profile(self, lab):
        wood = lab.get("wood")
        assert wood is not None
        assert wood.density == 0.7
        assert wood.hardness == 0.4

    def test_metal_profile(self, lab):
        metal = lab.get("metal")
        assert metal is not None
        assert metal.hardness == 0.9
        assert metal.resonance == 0.9

    def test_glass_profile(self, lab):
        glass = lab.get("glass")
        assert glass is not None
        assert glass.brightness == 0.9

    def test_create_fictional_material(self, lab):
        alien = lab.create_fictional("alien crystal", "glass", {"resonance": 0.95, "brightness": 0.99})
        assert alien.name == "alien crystal"
        assert alien.resonance == 0.95

    def test_create_custom_material(self, lab):
        custom = lab.create("my_plastic", density=1.2, hardness=0.6, resonance=0.5)
        assert custom.name == "my_plastic"
        assert custom.density == 1.2

    def test_interaction_sound(self, lab):
        result = lab.interaction_sound("metal", "wood", impact_force=1.0, velocity=2.0, mass=5.0)
        assert "combined_hardness" in result
        assert "sharpness" in result
        assert result["sharpness"] > 0

    def test_consistent_hash(self, lab):
        m1 = lab.get("wood")
        m2 = lab.get("wood")
        assert m1 is not None and m2 is not None
        assert m1.hash == m2.hash

    def test_save_load(self, lab, tmp_path):
        path = str(tmp_path / "materials.json")
        lab.save(path)
        loaded = MaterialSoundLab.load(path)
        assert loaded.get("wood") is not None
        assert loaded.get("metal") is not None

    def test_material_to_dict(self, lab):
        wood = lab.get("wood")
        d = wood.to_dict()
        assert d["name"] == "wood"
        assert "hash" in d
        assert d["density"] == 0.7

    def test_fictional_from_nonexistent(self, lab):
        result = lab.create_fictional("custom_thing", "nonexistent", {"density": 0.5})
        assert result.name == "custom_thing"
        assert result.density == 0.5

    def test_all_materials_have_params(self, lab):
        for name in lab.list_materials():
            m = lab.get(name)
            assert 0.0 <= m.density <= 10.0
            assert 0.0 <= m.hardness <= 1.0
            assert 0.0 <= m.resonance <= 1.0
