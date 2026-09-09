"""Tests for Audio Reconstruction."""
import numpy as np
import pytest
from app.make_model.audio.audio_reconstruction import (
    AudioReconstructor, ReconstructionResult, ReconstructionRecord,
)


class TestAudioReconstruction:
    @pytest.fixture
    def reconstructor(self):
        return AudioReconstructor(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_reconstructor_creation(self, reconstructor):
        assert reconstructor.sample_rate == 16000
        assert len(reconstructor.history) == 0

    def test_repair_clipping(self, reconstructor, test_audio):
        clipped = test_audio.copy()
        clipped[100:120] = 0.99
        result, record = reconstructor.repair_clipping(clipped)
        assert isinstance(record, ReconstructionRecord)
        assert record.method == "clipping_repair"
        assert len(result) == len(clipped)
        assert np.max(np.abs(result[result < 0.99])) <= 0.99

    def test_repair_dropouts(self, reconstructor, test_audio):
        audio_with_dropout = test_audio.copy()
        audio_with_dropout[1000:1200] = 0.0
        result, records = reconstructor.repair_dropout(audio_with_dropout)
        assert len(records) > 0
        assert len(result) == len(audio_with_dropout)
        assert result[1100] != 0.0

    def test_repair_discontinuity(self, reconstructor, test_audio):
        audio_with_jump = test_audio.copy()
        audio_with_jump[500:502] = 1.0
        result, records = reconstructor.repair_discontinuity(audio_with_jump)
        assert len(records) > 0
        assert np.max(np.abs(result[499:503])) <= 0.99

    def test_reconstruct_gap(self, reconstructor, test_audio):
        audio_gap = test_audio.copy()
        audio_gap[2000:2100] = 0.0
        result, record = reconstructor.reconstruct_gap(audio_gap, 2000, 2100, "interpolation")
        assert record.method == "interpolation"
        assert record.start_sample == 2000
        assert record.end_sample == 2100

    def test_reconstruct_ambience(self, reconstructor, test_audio):
        audio_with_ambience = test_audio.copy()
        result, record = reconstructor.reconstruct_ambience(
            audio_with_ambience, (100, 200), (500, 600)
        )
        assert record.method == "ambience_continuity"
        assert result[500] != audio_with_ambience[500]

    def test_full_reconstruction(self, reconstructor, test_audio):
        result = reconstructor.full_reconstruction(test_audio)
        assert isinstance(result, ReconstructionResult)
        assert len(result.audio) == len(test_audio)
        assert len(result.steps) > 0
        assert 0 <= result.confidence <= 1

    def test_full_reconstruction_with_issues(self, reconstructor):
        t = np.arange(8000) / 16000
        audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio[100:120] = 0.99
        audio[2000:2100] = 0.0
        result = reconstructor.full_reconstruction(audio)
        assert len(result.steps) > 0
        assert result.confidence > 0

    def test_records_history_tracking(self, reconstructor, test_audio):
        clipped = test_audio.copy()
        clipped[50] = 0.99
        _, record1 = reconstructor.repair_clipping(clipped)
        result = reconstructor.full_reconstruction(clipped)
        assert len(reconstructor.history) >= 1

    def test_reconstruction_preserves_continuity(self, reconstructor, test_audio):
        audio_gap = test_audio.copy()
        original_mid = test_audio[2000]
        result, _ = reconstructor.reconstruct_gap(audio_gap, 2000, 2050)
        assert abs(result[1999] - test_audio[1999]) < 0.01
        assert abs(result[2051] - test_audio[2051]) < 0.01

    def test_reconstruct_gap_repeat_method(self, reconstructor, test_audio):
        audio = test_audio.copy()
        result, record = reconstructor.reconstruct_gap(audio, 100, 200, "repeat")
        assert record.method == "repeat"
        assert len(result) == len(audio)
