"""Tests for MAKE Image Engine identity, objects, camera, lighting, materials."""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.image.identity import IdentityGenome, IdentityEncoder, IdentityPreservationEngine
from app.make_model.image.objects import ObjectGenome, ObjectEncoder, ObjectManipulationEngine
from app.make_model.image.camera import CinemaCameraEngine
from app.make_model.image.lighting import LightingDirector, LightSetup
from app.make_model.image.materials import MaterialLab, MaterialProperties


def test_identity_genome():
    genome = IdentityGenome(identity_id="id1", embedding=np.ones(256, dtype=np.float32))
    assert genome.identity_id == "id1"
    d = genome.to_dict()
    assert d["has_embedding"] is True


def test_identity_encoder():
    enc = IdentityEncoder()
    feat = np.random.rand(128).astype(np.float32)
    out = enc(feat)
    assert out.shape == (1, 256)


def test_identity_preservation():
    engine = IdentityPreservationEngine()
    a = IdentityGenome(identity_id="a", embedding=np.ones(256, dtype=np.float32))
    b = IdentityGenome(identity_id="b", embedding=np.ones(256, dtype=np.float32))
    engine.register(a)
    assert engine.get("a") is a
    drift = engine.measure_drift(a, b)
    assert drift == 0.0


def test_object_genome():
    obj = ObjectGenome(object_id="obj1", label="cube", bbox=(0.0, 0.0, 1.0, 1.0))
    assert obj.object_id == "obj1"
    moved = obj.transform("move", {"dx": 0.1, "dy": 0.2})
    assert moved.bbox == (0.1, 0.2, 1.1, 1.2)


def test_object_encoder():
    enc = ObjectEncoder()
    feat = np.random.rand(128).astype(np.float32)
    out = enc(feat)
    assert out.shape == (1, 256)


def test_object_manipulation():
    engine = ObjectManipulationEngine()
    obj = ObjectGenome(object_id="obj1", label="cube", bbox=(0.0, 0.0, 1.0, 1.0))
    engine.register(obj)
    moved = engine.move("obj1", dx=0.1, dy=0.2)
    assert moved is not None
    assert moved.bbox == (0.1, 0.2, 1.1, 1.2)
    dup = engine.duplicate("obj1")
    assert dup is not None
    assert "dup" in dup.object_id


def test_cinema_camera_engine():
    engine = CinemaCameraEngine()
    preset = engine.get_preset("close_up")
    assert preset is not None
    assert preset.focal_length == 85.0
    current = engine.apply(preset, "wide")
    assert current.focal_length == 24.0


def test_lighting_director():
    director = LightingDirector()
    preset = director.get_preset("sunset")
    assert preset is not None
    assert preset.key_intensity == 0.9
    a = LightSetup(key_intensity=1.0)
    b = LightSetup(key_intensity=0.0)
    blended = director.blend(a, b, weight=0.5)
    assert blended.key_intensity == 0.5


def test_material_lab():
    lab = MaterialLab()
    plastic = lab.get_preset("plastic")
    assert plastic is not None
    assert plastic.metallic == 0.0
    glass = lab.get_preset("glass")
    assert glass.transmission == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
