"""Tests for Spatial Audio V3."""
import numpy as np
import pytest
from app.make_model.audio.spatial_engine_v3 import (
    SpatialEngineV3, Source, Listener, Room, HRTFDatabase, SpatialEvent,
)


class TestSpatialAudioV3:
    @pytest.fixture
    def engine(self):
        return SpatialEngineV3(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_engine_creation(self, engine):
        assert engine.sample_rate == 16000
        assert isinstance(engine.listener, Listener)
        assert isinstance(engine.room, Room)

    def test_add_source(self, engine):
        src = Source(azimuth=30, elevation=10, distance=5.0, id="s1")
        engine.add_source(src)
        assert len(engine.sources) == 1

    def test_set_listener(self, engine):
        engine.set_listener((1.0, 2.0, 3.0), forward=(0.0, 1.0, 0.0))
        assert engine.listener.position == (1.0, 2.0, 3.0)
        assert engine.listener.forward == (0.0, 1.0, 0.0)

    def test_set_room(self, engine):
        room = Room(dimensions=(8, 6, 4), wall_material="wood", absorption=0.2, rt60=0.5)
        engine.set_room(room)
        assert engine.room.wall_material == "wood"

    def test_itd_computation(self, engine):
        itd = engine.compute_itd(30)
        assert abs(itd) > 0
        assert abs(itd) < 0.001
        itd_left = engine.compute_itd(-90)
        itd_right = engine.compute_itd(90)
        assert abs(itd_left + itd_right) < 1e-6

    def test_ild_computation(self, engine):
        ild_low = engine.compute_ild(45, "low")
        ild_high = engine.compute_ild(45, "high")
        assert ild_high > ild_low

    def test_distance_attenuation(self, engine):
        att1 = engine.compute_distance_attenuation(1.0)
        att2 = engine.compute_distance_attenuation(4.0)
        assert att2 < att1

    def test_occlusion(self, engine):
        occ_none = engine.compute_occlusion(0.0)
        occ_full = engine.compute_occlusion(1.0)
        assert occ_none == 1.0
        assert occ_full < 1.0

    def test_spatialize_mono_source(self, engine, test_audio):
        src = Source(azimuth=45, elevation=10, distance=3.0)
        result = engine.spatialize_mono_source(test_audio, src)
        assert result.shape[1] == 2
        assert np.max(np.abs(result)) <= 0.99

    def test_spatialize_opposite_directions(self, engine, test_audio):
        left = engine.spatialize_mono_source(test_audio, Source(azimuth=-60, distance=3.0))
        right = engine.spatialize_mono_source(test_audio, Source(azimuth=60, distance=3.0))
        left_level = np.mean(np.abs(left[:, 0]))
        right_level = np.mean(np.abs(right[:, 0]))

    def test_room_response(self, engine, test_audio):
        src = Source(0, 0, 3.0)
        stereo = engine.spatialize_mono_source(test_audio, src)
        result = engine.apply_room_response(stereo)
        assert result.shape == stereo.shape
        assert np.max(np.abs(result)) <= 0.99

    def test_stereo_width(self, engine):
        audio = np.column_stack([test_audio, test_audio])
        stereo = np.column_stack([test_audio, test_audio * 0.8])
        result = engine.apply_stereo_width(stereo, width=0.5)
        assert result.shape == stereo.shape

    def test_source_movement(self, engine, test_audio):
        path = [(30, 0, 5), (60, 10, 3), (-30, 0, 2)]
        result = engine.process_source_movement(test_audio, path, 0.5)
        assert result.ndim == 2 or result.ndim == 1
        assert result.shape[1] == 2
        assert np.max(np.abs(result)) <= 0.99

    def test_multiple_sources(self, engine, test_audio):
        audio_b = test_audio * 0.5
        sources = [Source(30, 0, 3.0, "s1"), Source(-30, 0, 5.0, "s2")]
        result = engine.process_multiple_sources([test_audio, audio_b], sources)
        assert result.shape[1] == 2

    def test_hrtf_availability(self):
        hrtf = HRTFDatabase()
        assert hrtf.available is False

    def test_hrtf_load_invalid(self):
        hrtf = HRTFDatabase()
        assert hrtf.load_hrtf("/nonexistent/hrtf.npz") is False
        assert hrtf.available is False

    def test_hrtf_interpolate_unavailable(self):
        hrtf = HRTFDatabase()
        left, right = hrtf.interpolate(30, 10)
        assert left.shape[0] == 3
        assert right.shape[0] == 3
