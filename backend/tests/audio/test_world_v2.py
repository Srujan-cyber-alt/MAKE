"""Tests for audio world, room, material, object acoustics, material interaction."""

import pytest

from app.make_model.audio.audio_world import AudioWorld, Person, Vehicle, Machinery, Weather, CrowdDensity
from app.make_model.audio.room import Room
from app.make_model.audio.material import Material, MATERIAL_LIBRARY, get_material
from app.make_model.audio.object_acoustics import ObjectAcoustics
from app.make_model.audio.material_interaction import MaterialInteraction


class TestRoom:
    def test_basic_room(self):
        room = Room(room_id="r1", size="medium", width=5.0, length=6.0, height=3.0)
        assert room.volume == 90.0
        assert room.surface_area == 126.0

    def test_rt60_estimate(self):
        room = Room(room_id="r1", absorption=0.5, volume=100.0, surface_area=200.0)
        rt60 = room.estimate_rt60()
        assert rt60 > 0.0

    def test_to_dict_roundtrip(self):
        room = Room(room_id="r1")
        data = room.to_dict()
        restored = Room.from_dict(data)
        assert restored.room_id == "r1"


class TestMaterial:
    def test_material_library(self):
        for name in ["wood", "metal", "glass", "plastic", "stone", "fabric", "water", "paper", "rubber", "concrete", "leather"]:
            assert name in MATERIAL_LIBRARY
            assert MATERIAL_LIBRARY[name].absorption >= 0.0

    def test_get_material_fallback(self):
        mat = get_material("unknown_material")
        assert mat.material_id == "fabric"

    def test_to_dict_roundtrip(self):
        mat = MATERIAL_LIBRARY["wood"]
        data = mat.to_dict()
        restored = Material.from_dict(data)
        assert restored.material_id == "wood"


class TestObjectAcoustics:
    def test_impact_response(self):
        obj = ObjectAcoustics(object_id="o1", mass=2.0, stiffness=0.8)
        response = obj.impact_response(force=1.0)
        assert response["amplitude"] > 0.0
        assert response["frequency"] > 0.0

    def test_to_dict_roundtrip(self):
        obj = ObjectAcoustics(object_id="o1")
        data = obj.to_dict()
        restored = ObjectAcoustics.from_dict(data)
        assert restored.object_id == "o1"


class TestMaterialInteraction:
    def test_from_materials(self):
        interaction = MaterialInteraction.from_materials("wood", "metal")
        assert interaction.material_a == "wood"
        assert interaction.material_b == "metal"
        assert interaction.impact_absorption > 0.0

    def test_to_dict_roundtrip(self):
        interaction = MaterialInteraction.from_materials("glass", "fabric")
        data = interaction.to_dict()
        restored = MaterialInteraction.from_dict(data)
        assert restored.material_a == "glass"


class TestAudioWorld:
    def test_add_room(self):
        world = AudioWorld("w1")
        world.add_room(Room(room_id="r1"))
        assert world.get_room("r1") is not None

    def test_add_person(self):
        world = AudioWorld("w1")
        world.add_person(Person(person_id="p1"))
        assert world.people["p1"].person_id == "p1"

    def test_add_vehicle(self):
        world = AudioWorld("w1")
        world.add_vehicle(Vehicle(vehicle_id="v1"))
        assert world.vehicles["v1"].vehicle_id == "v1"

    def test_add_machinery(self):
        world = AudioWorld("w1")
        world.add_machinery(Machinery(machine_id="m1"))
        assert world.machinery["m1"].machine_id == "m1"

    def test_weather(self):
        world = AudioWorld("w1")
        world.weather = Weather.RAIN
        assert world.weather == Weather.RAIN

    def test_crowd_density(self):
        world = AudioWorld("w1")
        world.crowd_density = CrowdDensity.DENSE
        assert world.crowd_density == CrowdDensity.DENSE

    def test_to_dict_roundtrip(self):
        world = AudioWorld("w1")
        world.add_room(Room(room_id="r1"))
        data = world.to_dict()
        restored = AudioWorld.from_dict(data)
        assert restored.get_room("r1") is not None