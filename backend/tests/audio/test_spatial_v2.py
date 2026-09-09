"""Tests for spatial engine and audio camera."""

import numpy as np
import pytest

from app.make_model.audio.spatial_engine import SpatialEngine, SpatialSource, SpatialModel, ListenerPosition
from app.make_model.audio.audio_camera import AudioCamera


class TestSpatialEngine:
    def test_stereo_spatialize(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        source = SpatialSource(source_id="s1", azimuth=30.0, distance=1.0)
        result = engine.spatialize(audio, source)
        assert result.shape[0] == audio.size
        assert result.shape[1] == 2

    def test_distance_attenuation(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        near = engine.spatialize(audio, SpatialSource(source_id="s1", distance=0.5))
        far = engine.spatialize(audio, SpatialSource(source_id="s1", distance=5.0))
        assert np.max(np.abs(near)) > np.max(np.abs(far))

    def test_occlusion(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = engine.spatialize(audio, SpatialSource(source_id="s1", occlusion=1.0))
        assert result.shape[1] == 2

    def test_create_scene(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        sources = [SpatialSource(source_id="s1", azimuth=-30.0), SpatialSource(source_id="s2", azimuth=30.0)]
        scene = engine.create_scene(sources, ListenerPosition(), {"s1": audio, "s2": audio})
        assert scene.shape[1] == 2
        assert scene.size > 0

    def test_available_models(self):
        engine = SpatialEngine()
        models = engine.available_models()
        assert len(models) == 4
        assert "stereo" in models
        assert "ambisonic" in models

    def test_elevation_attenuation(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        low = engine.spatialize(audio, SpatialSource(source_id="s1", elevation=0.0))
        high = engine.spatialize(audio, SpatialSource(source_id="s1", elevation=90.0))
        assert np.max(np.abs(low)) >= np.max(np.abs(high))

    def test_gain(self):
        engine = SpatialEngine(model=SpatialModel.BINAURAL, sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        quiet = engine.spatialize(audio, SpatialSource(source_id="s1", gain=0.1))
        loud = engine.spatialize(audio, SpatialSource(source_id="s1", gain=1.0))
        assert np.max(np.abs(quiet)) < np.max(np.abs(loud))

    def test_empty_audio(self):
        engine = SpatialEngine()
        result = engine.spatialize(np.array([], dtype=np.float32), SpatialSource(source_id="s1"))
        assert result.size == 0


class TestAudioCamera:
    def test_constructor(self):
        camera = AudioCamera(camera_id="cam1")
        assert camera.camera_id == "cam1"

    def test_forward_vector(self):
        camera = AudioCamera(camera_id="cam1")
        camera.look_at = (1.0, 0.0, 0.0)
        fwd = camera.forward_vector()
        assert fwd[0] > 0.9

    def test_visible_sources(self):
        camera = AudioCamera(camera_id="cam1", fov=120.0)
        camera.look_at = (1.0, 0.0, 0.0)
        s1 = SpatialSource(source_id="s1", azimuth=0.0, distance=1.0)
        s2 = SpatialSource(source_id="s2", azimuth=180.0, distance=1.0)
        visible = camera.visible_sources([s1, s2])
        assert s1 in visible
        assert s2 not in visible

    def test_to_dict_roundtrip(self):
        camera = AudioCamera(camera_id="cam1")
        data = camera.to_dict()
        restored = AudioCamera.from_dict(data)
        assert restored.camera_id == "cam1"

    def test_far_clip(self):
        camera = AudioCamera(camera_id="cam1", far_clip=10.0)
        assert camera.far_clip == 10.0

    def test_up_vector(self):
        camera = AudioCamera(camera_id="cam1", up=(0.0, 0.0, 1.0))
        assert camera.up == (0.0, 0.0, 1.0)

    def test_yaw_forward(self):
        camera = AudioCamera(camera_id="cam1")
        camera.position.yaw = 90.0
        fwd = camera.forward_vector()
        assert fwd[1] > 0.9