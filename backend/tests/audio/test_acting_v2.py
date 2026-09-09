"""Tests for Acting Engine V2."""
import numpy as np
import pytest
from app.make_model.audio.acting_v2 import (
    ActingEngine, ActingStyle, ActingStyleParams,
    ACTING_STYLE_TABLE,
)


class TestActingEngine:
    @pytest.fixture
    def engine(self):
        return ActingEngine(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(16000) / 16000
        return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    def test_engine_creation(self, engine):
        assert engine.sample_rate == 16000
        assert engine.default_style == ActingStyle.NEUTRAL

    def test_all_14_cinematic_styles_present(self):
        expected = {"whisper", "shout", "restrained", "nervous", "sarcastic",
                    "confident", "hesitant", "intimate", "authoritative",
                    "exhausted", "crying", "laughing", "breathy", "dramatic"}
        actual = {s.value for s in ActingStyle}
        assert expected.issubset(actual)

    def test_get_style_params(self, engine):
        params = engine.get_style_params(ActingStyle.WHISPER)
        assert isinstance(params, ActingStyleParams)
        assert params.volume_mult < 1.0

    def test_apply_whisper(self, engine, test_audio):
        result = engine.apply_style(test_audio, ActingStyle.WHISPER)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99
        whisper_level = np.sqrt(np.mean(result ** 2))
        assert whisper_level < np.sqrt(np.mean(test_audio ** 2))

    def test_apply_shout(self, engine, test_audio):
        result = engine.apply_style(test_audio, ActingStyle.SHOUT)
        assert np.max(np.abs(result)) <= 0.99
        shout_level = np.sqrt(np.mean(result ** 2))
        original_level = np.sqrt(np.mean(test_audio ** 2))
        assert shout_level > original_level

    def test_apply_confident(self, engine, test_audio):
        result = engine.apply_style(test_audio, ActingStyle.CONFIDENT)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_determinism(self, engine, test_audio):
        r1 = engine.apply_style(test_audio, ActingStyle.WHISPER)
        r2 = engine.apply_style(test_audio, ActingStyle.WHISPER)
        assert np.allclose(r1, r2)

    def test_emotion_continuity(self, engine, test_audio):
        timeline = [
            {"happiness": 0.3, "anger": 0.1, "fear": 0.05, "urgency": 0.1},
            {"happiness": 0.6, "anger": 0.3, "fear": 0.2, "urgency": 0.5},
            {"happiness": 0.2, "anger": 0.7, "fear": 0.4, "urgency": 0.8},
        ]
        result = engine.apply_emotion_continuity(test_audio, timeline)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_emotion_conflict_detection(self, engine, test_audio):
        timeline = [
            {"happiness": 0.2, "calm": 0.8},
            {"happiness": 0.9, "anger": 0.1},
            {"happiness": 0.1, "anger": 0.9},
        ]
        result = engine.apply_emotion_continuity(test_audio, timeline)
        assert len(result) > 0

    def test_acting_to_sentence(self, engine, test_audio):
        text = "hello world this is a test sentence"
        emotions = [
            {"anger": 0.1, "confidence": 0.5},
            {"anger": 0.5, "confidence": 0.6},
            {"anger": 0.3, "confidence": 0.7},
            {"anger": 0.2, "confidence": 0.8},
            {"anger": 0.1, "confidence": 0.9},
            {"anger": 0.0, "confidence": 1.0},
        ]
        pauses = [0.1, 0.05, 0.2, 0.05, 0.1]
        result = engine.apply_acting_to_sentence(text, test_audio, emotions, pauses)
        assert len(result) > len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_breath_generation(self, engine):
        breaths = engine.generate_breath_samples(2)
        assert len(breaths) == 2
        for breath in breaths:
            assert len(breath) > 0
            assert np.max(np.abs(breath)) <= 0.99

    def test_hesitation_insertion(self, engine, test_audio):
        result = engine.generate_hesitation(test_audio, position=0.5)
        assert len(result) > len(test_audio)

    def test_overlapping_speech(self, engine, test_audio):
        audio_b = test_audio * 0.8
        result = engine.overlapping_speech(test_audio, audio_b, offset_b=0.3)
        assert len(result) > len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_style_table_complete(self):
        assert len(ACTING_STYLE_TABLE) >= 16

    def test_pitch_shift(self, engine, test_audio):
        result = engine._apply_pitch_shift(test_audio, 4.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_rate_change(self, engine, test_audio):
        result = engine._apply_rate(test_audio, 1.2)
        assert len(result) >= int(len(test_audio) * 0.8)

    def test_breathiness_application(self, engine, test_audio):
        result = engine._apply_breathiness(test_audio, 0.8)
        assert np.max(np.abs(result)) <= 0.99

    def test_tremor_application(self, engine, test_audio):
        result = engine._apply_tremor(test_audio, freq=5.0, depth=0.2)
        assert np.max(np.abs(result)) <= 0.99

    def test_jitter_shimmer(self, engine, test_audio):
        result = engine._apply_jitter_shimmer(test_audio, jitter=0.1, shimmer=0.05)
        assert np.max(np.abs(result)) <= 0.99
