"""Tests for MAKE Image Engine architecture."""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.image.arch import (
    ImageConfig,
    ImageFoundationModel,
    TextEncoder,
    VisionEncoder,
    IdentityEncoder,
    ObjectEncoder,
    SceneEncoder,
    SpatialEncoder,
    LatentCodec,
    DetailRefiner,
    SuperResolutionModule,
    QualityController,
)


def test_image_config_tiny():
    cfg = ImageConfig.from_preset("TINY")
    assert cfg.hidden_dim == 64
    assert cfg.num_layers == 2


def test_text_encoder():
    enc = TextEncoder()
    tokens = np.array([1, 2, 3, 4], dtype=np.int64)
    out = enc(tokens)
    assert out.shape == (1, 256)


def test_vision_encoder():
    enc = VisionEncoder()
    img = np.random.rand(3, 64, 64).astype(np.float32)
    out = enc(img)
    assert out.shape == (1, 256)


def test_identity_encoder():
    enc = IdentityEncoder()
    feat = np.random.rand(128).astype(np.float32)
    out = enc(feat)
    assert out.shape == (1, 256)


def test_object_encoder():
    enc = ObjectEncoder()
    feat = np.random.rand(128).astype(np.float32)
    out = enc(feat)
    assert out.shape == (1, 256)


def test_scene_encoder():
    enc = SceneEncoder()
    feat = np.random.rand(128).astype(np.float32)
    out = enc(feat)
    assert out.shape == (1, 256)


def test_spatial_encoder():
    enc = SpatialEncoder()
    coords = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    out = enc(coords)
    assert out.shape == (2, 128)


def test_latent_codec_roundtrip():
    codec = LatentCodec()
    img = np.random.rand(1, 3, 64, 64).astype(np.float32)
    latent = codec.encode(img)
    decoded = codec.decode(latent)
    assert decoded.shape == img.shape


def test_detail_refiner():
    refiner = DetailRefiner()
    latent = np.random.rand(1, 4, 32, 32).astype(np.float32)
    out = refiner(latent)
    assert out.shape == latent.shape


def test_super_resolution():
    sr = SuperResolutionModule(scale=2)
    img = np.random.rand(1, 3, 32, 32).astype(np.float32)
    out = sr(img)
    assert out.shape == (1, 3, 64, 64)


def test_quality_controller():
    qc = QualityController()
    img = np.random.rand(1, 3, 64, 64).astype(np.float32)
    metrics = qc.assess(img)
    assert "sharpness" in metrics
    assert "contrast" in metrics


def test_image_foundation_model_tiny():
    cfg = ImageConfig.from_preset("TINY")
    model = ImageFoundationModel(cfg)
    assert model.parameter_count() > 0
    x = np.random.rand(1, 3, 32, 32).astype(np.float32)
    t = np.array([0.5], dtype=np.float32)
    text = np.zeros((1, 16), dtype=np.int64)
    out = model.forward(x, t, text)
    assert out.shape == (1, 4, 32, 32)


def test_parameter_save_load():
    cfg = ImageConfig.from_preset("TINY")
    model = ImageFoundationModel(cfg)
    params = model.parameters()
    model.load_parameters(params)
    assert model.parameter_count() == sum(v.size for v in params.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
