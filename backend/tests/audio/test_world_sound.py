"""Tests for World Sound Intelligence."""
import numpy as np
import pytest
from app.make_model.audio.world_sound import (
    WorldSoundIntelligence, WorldSoundModel, Surface, Door, Window,
    RoomObject, AcousticProperties, MATERIAL_ABSORPTION,
)


class TestWorldSound:
    @pytest.fixture
    def world(self):
        return WorldSoundIntelligence()

    def test_world_creation(self, world):
        assert len(world.rooms) >= 3
        assert "bedroom" in world.rooms
        assert "bathroom" in world.rooms
        assert "cave" in world.rooms

    def test_create_room(self, world):
        room = world.create_room(
            name="test_room",
            dimensions=(5.0, 4.0, 3.0),
            floor_material="wood",
            wall_material="concrete",
            ceiling_material="drywall",
        )
        assert room.name == "test_room"
        assert len(room.surfaces) == 6
        assert room.acoustic_props is not None

    def test_get_room(self, world):
        room = world.get_room("bedroom")
        assert room is not None
        assert room.floor_material == "carpet"

    def test_get_room_not_found(self, world):
        assert world.get_room("nonexistent") is None

    def test_acoustic_properties(self, world):
        room = world.create_room("test", (4, 3, 2.5), "wood", "concrete", "drywall")
        props = room.acoustic_props
        assert isinstance(props, AcousticProperties)
        assert props.rt60_125 > 0
        assert props.clarity > 0
        assert props.definition > 0

    def test_reason_about_sound(self, world):
        audio = np.sin(2 * np.pi * 440 * np.arange(1600) / 16000).astype(np.float32)
        result = world.reason_about_sound(audio, "wood", "bedroom", distance=3.0)
        assert "attenuation" in result
        assert "expected_reverb_time" in result
        assert "clarity" in result

    def test_reason_invalid_room(self, world):
        audio = np.zeros(100)
        result = world.reason_about_sound(audio, "wood", "nonexistent", 1.0)
        assert "error" in result

    def test_footstep_on_material(self, world):
        result = world.footstep_on_material("wood", force=1.0)
        assert "resonance" in result
        assert "loudness" in result
        assert "sharpness" in result
        assert "absorption" in result
        assert 0 <= result["loudness"] <= 1

    def test_footstep_material_comparison(self, world):
        materials = ["wood", "metal", "glass", "stone", "carpet"]
        results = world.simulate_material_interactions(materials)
        assert len(results) == 5
        assert "contrast_ratios" in results

    def test_carpet_vs_metal(self, world):
        carpet = world.footstep_on_material("carpet")
        metal = world.footstep_on_material("metal")
        assert metal["resonance"] > carpet["resonance"]
        assert carpet["loudness"] < metal["loudness"]

    def test_all_materials_supported(self, world):
        materials = list(MATERIAL_ABSORPTION.keys())
        for mat in materials:
            result = world.footstep_on_material(mat)
            assert "resonance" in result
            assert "loudness" in result

    def test_room_with_objects_doors_windows(self, world):
        obj = RoomObject("chair", (2, 2, 0), "wood", 0.5)
        door_obj = Door((1, 0, 1), 0.8, 2.0, open=True)
        window_obj = Window((3, 0, 1.5), 1.0, 0.8)
        room = world.create_room(
            "furnished",
            (5, 4, 3),
            "wood", "concrete", "drywall",
            objects=[obj],
            doors=[door_obj],
            windows=[window_obj],
        )
        assert len(room.objects) == 1
        assert len(room.doors) == 1
        assert len(room.windows) == 1

    def test_room_dimensions_affect_acoustics(self, world):
        small = world.create_room("small", (2, 2, 2), "wood", "concrete", "drywall")
        large = world.create_room("large", (10, 10, 10), "wood", "concrete", "drywall")
        if small.acoustic_props and large.acoustic_props:
            assert large.acoustic_props.reverb_time >= small.acoustic_props.reverb_time
