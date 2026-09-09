"""Tests for Spatial Audio V2 Engine."""
from __future__ import annotations
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
import tempfile, os
from app.make_model.audio.spatial_engine import SpatialEngine, Listener, Room, Source

def _make_wav(path, sr=16000, duration=1.0):
    t = np.linspace(0, duration, int(sr*duration), endpoint=False)
    audio = 0.3 * np.sin(2*np.pi*220*t)
    wavfile.write(path, sr, (audio*32767).astype(np.int16))
    return path

class TestSpatialEngine:
    @pytest.fixture
    def engine(self):
        return SpatialEngine(sample_rate=16000)

    @pytest.fixture
    def test_wav(self, tmp_path):
        path = str(tmp_path / "test.wav")
        _make_wav(path)
        return path

    def test_basic_spatialize(self, engine, test_wav):
        result = engine.spatialize(test_wav, (3.0, 0.0, 0.0))
        assert os.path.exists(result.audio_path)
        assert result.channels == 2

    def test_distance_attenuation(self, engine, test_wav):
        near = engine.spatialize(test_wav, (0.5, 0.0, 0.0))
        far = engine.spatialize(test_wav, (5.0, 0.0, 0.0))
        sr_n, data_n = wavfile.read(near.audio_path)
        sr_f, data_f = wavfile.read(far.audio_path)
        near_rms = np.sqrt(np.mean(data_n**2))
        far_rms = np.sqrt(np.mean(data_f**2))
        assert far_rms < near_rms

    def test_left_right_panning(self, engine, test_wav):
        left = engine.spatialize(test_wav, (-5.0, 0.0, 0.0))
        right = engine.spatialize(test_wav, (5.0, 0.0, 0.0))
        sr_l, data_l = wavfile.read(left.audio_path)
        sr_r, data_r = wavfile.read(right.audio_path)
        left_channel_l = data_l[:, 0] if data_l.ndim > 1 else data_l
        right_channel_l = data_l[:, 1] if data_l.ndim > 1 else data_l
        assert np.mean(np.abs(left_channel_l)) > np.mean(np.abs(right_channel_l))
        left_channel_r = data_r[:, 0] if data_r.ndim > 1 else data_r
        right_channel_r = data_r[:, 1] if data_r.ndim > 1 else data_r
        assert np.mean(np.abs(right_channel_r)) > np.mean(np.abs(left_channel_r))

    def test_calculate_spatialization(self, engine):
        result = engine.calculate_spatialization((3.0, 4.0, 0.0))
        assert result["distance"] == pytest.approx(5.0, abs=0.1)
        assert -180 <= result["azimuth"] <= 180
        assert 0.0 <= result["left_gain"] <= 1.0
        assert 0.0 <= result["right_gain"] <= 1.0

    def test_deterministic(self, engine, test_wav):
        r1 = engine.spatialize(test_wav, (3.0, 4.0, 0.0))
        r2 = engine.spatialize(test_wav, (3.0, 4.0, 0.0))
        sr1, d1 = wavfile.read(r1.audio_path)
        sr2, d2 = wavfile.read(r2.audio_path)
        assert len(d1) == len(d2)
        np.testing.assert_array_equal(d1, d2)

    def test_occlusion(self, engine, test_wav):
        no_occ = engine.spatialize(test_wav, (3.0, 0.0, 0.0), occlusion=0.0)
        occ = engine.spatialize(test_wav, (3.0, 0.0, 0.0), occlusion=0.5)
        sr1, d1 = wavfile.read(no_occ.audio_path)
        sr2, d2 = wavfile.read(occ.audio_path)
        rms1 = np.sqrt(np.mean(d1**2))
        rms2 = np.sqrt(np.mean(d2**2))
        assert rms2 < rms1

    def test_provenance(self, engine, test_wav):
        result = engine.spatialize(test_wav, (3.0, 0.0, 0.0))
        assert "method" in result.provenance
        assert result.provenance["method"] == "ITD/ILD approximation (no HRTF data)"

    def test_create_scene(self, engine, test_wav):
        sources = [
            Source(audio_path=test_wav, position=(3.0, 0.0, 0.0)),
            Source(audio_path=test_wav, position=(0.0, 4.0, 0.0)),
        ]
        result = engine.create_scene(sources)
        assert os.path.exists(result.audio_path)
        assert result.channels == 2

    def test_room_setting(self, engine, test_wav):
        engine.set_room(Room(width=10.0, length=8.0, height=4.0, rt60=1.2))
        result = engine.spatialize(test_wav, (5.0, 3.0, 0.0))
        assert result.provenance["room_rt60"] == 1.2

    def test_elevation_handling(self, engine, test_wav):
        result = engine.spatialize(test_wav, (3.0, 0.0, 5.0))
        assert "elevation" in result.provenance
        assert result.provenance["elevation"] > 0
