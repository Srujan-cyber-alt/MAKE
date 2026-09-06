"""Tests for MAKE Image Engine conditioning."""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.image.conditioning import (
    ConditioningBundle,
    ConditioningEngine,
    compose_conditioning,
)


def test_conditioning_bundle_empty():
    bundle = ConditioningBundle()
    d = bundle.to_dict()
    assert "seed" in d


def test_compose_text_only():
    bundle = compose_conditioning(text="a cinematic portrait")
    assert bundle.text_emb is not None
    assert bundle.text_emb.shape[-1] == 256


def test_compose_multimodal():
    bundle = compose_conditioning(
        text="a person in Tokyo",
        image=np.random.rand(3, 64, 64).astype(np.float32),
        identity=np.random.rand(128).astype(np.float32),
        camera={"focal_length": 50.0, "aperture": 2.8},
        lighting={"key_intensity": 1.0, "key_color": (1.0, 0.95, 0.9)},
    )
    assert bundle.text_emb is not None
    assert bundle.image_emb is not None
    assert bundle.identity_emb is not None
    assert bundle.camera_emb is not None
    assert bundle.lighting_emb is not None


def test_conditioning_engine():
    engine = ConditioningEngine()
    bundle = compose_conditioning(text="test")
    composed = engine.compose(bundle)
    assert composed.shape == (1, 256)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
