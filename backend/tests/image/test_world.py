"""Tests for MAKE Image Engine world representation."""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.image.world import (
    Camera,
    Lighting,
    Material,
    Object,
    Human,
    Relationship,
    Scene,
    WorldState,
    WorldRepresentation,
    RealityDNA,
    WorldFork,
    CameraTeleport,
    TimeMachine,
    PersistentWorldState,
)


def test_camera_creation():
    cam = Camera(position=(0.0, 0.0, 1.0), focal_length=50.0)
    assert cam.focal_length == 50.0
    d = cam.to_dict()
    assert d["focal_length"] == 50.0


def test_lighting_creation():
    light = Lighting(light_type="sunlight", key_intensity=1.0)
    assert light.light_type == "sunlight"
    d = light.to_dict()
    assert d["key_intensity"] == 1.0


def test_material_creation():
    mat = Material(base_color=(1.0, 0.0, 0.0), metallic=1.0)
    assert mat.metallic == 1.0
    d = mat.to_dict()
    assert d["base_color"] == [1.0, 0.0, 0.0]


def test_object_creation():
    obj = Object(object_id="obj1", label="cube")
    assert obj.object_id == "obj1"
    d = obj.to_dict()
    assert d["label"] == "cube"


def test_human_creation():
    human = Human(human_id="person1", expression="neutral")
    assert human.human_id == "person1"
    d = human.to_dict()
    assert d["expression"] == "neutral"


def test_relationship_creation():
    rel = Relationship(subject_id="person1", predicate="holding", object_id="cup1")
    assert rel.predicate == "holding"
    d = rel.to_dict()
    assert d["object_id"] == "cup1"


def test_scene_creation():
    scene = Scene(scene_id="scene1", camera=Camera(), lighting=Lighting())
    scene.add_object(Object(object_id="obj1"))
    scene.add_human(Human(human_id="person1"))
    scene.add_relationship(Relationship(subject_id="person1", predicate="holding", object_id="obj1"))
    assert len(scene.objects) == 1
    assert len(scene.humans) == 1
    assert len(scene.relationships) == 1
    d = scene.to_dict()
    assert d["scene_id"] == "scene1"


def test_world_state():
    state = WorldState(world_id="world1")
    state.add_scene(Scene(scene_id="s1"))
    state.record_edit("add_object", {"object_id": "obj1"})
    assert len(state.scenes) == 1
    assert len(state.edit_history) == 1
    d = state.to_dict()
    assert d["world_id"] == "world1"


def test_reality_dna():
    dna = RealityDNA(world_id="world1")
    d = dna.to_dict()
    assert d["world_id"] == "world1"


def test_world_representation():
    world = WorldRepresentation(world_id="w1")
    scene = Scene(scene_id="s1", camera=Camera(), lighting=Lighting())
    world.add_scene(scene)
    dna = world.extract_reality_dna("s1")
    assert dna.world_id == "w1"
    cam = world.camera_teleport("s1", "close_up")
    assert cam is not None
    light = world.time_machine("s1", "night")
    assert light is not None


def test_camera_teleport():
    scene = Scene(scene_id="s1", camera=Camera())
    teleport = CameraTeleport(scene)
    presets = teleport.presets()
    assert "front" in presets
    assert "close_up" in presets


def test_time_machine():
    scene = Scene(scene_id="s1", lighting=Lighting())
    machine = TimeMachine(scene)
    lighting = machine.set_time_of_day("sunset")
    assert lighting.light_type == "sunlight"


def test_persistent_world_state():
    state = WorldState(world_id="w1")
    state.add_scene(Scene(scene_id="s1"))
    pws = PersistentWorldState(state)
    edited = pws.apply_edit("test_edit", {"key": "value"})
    assert len(edited.edit_history) == 1


def test_world_fork():
    state = WorldState(world_id="w1")
    state.add_scene(Scene(scene_id="s1", lighting=Lighting(key_intensity=1.0)))
    fork = WorldFork(state)
    new_state = fork.create_alternate("s1", {"lighting": Lighting(key_intensity=0.5)})
    assert "fork" in new_state.world_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
