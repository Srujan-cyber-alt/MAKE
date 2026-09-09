"""Tests for continuous emotion and emotion timeline/transition modules."""

import math

import numpy as np
import pytest

from app.make_model.audio.continuous_emotion import ContinuousEmotion
from app.make_model.audio.emotion_timeline import EmotionTimeline, EmotionKeyframe
from app.make_model.audio.emotion_transition import EmotionTransition, LINEAR, SIGMOID, COSINE, CUBIC


class TestContinuousEmotion:
    def test_neutral_defaults(self):
        e = ContinuousEmotion.neutral()
        assert e.valence == 0.5
        assert e.arousal == 0.5

    def test_from_dict_clamps(self):
        e = ContinuousEmotion.from_dict({"valence": 2.0, "arousal": -1.0})
        assert e.valence == 1.0
        assert e.arousal == 0.0

    def test_blend(self):
        a = ContinuousEmotion(valence=0.9, arousal=0.8)
        b = ContinuousEmotion(valence=0.1, arousal=0.2)
        blended = a.blend(b, weight=0.5)
        assert abs(blended.valence - 0.5) < 1e-6
        assert abs(blended.arousal - 0.5) < 1e-6

    def test_distance(self):
        a = ContinuousEmotion(valence=0.9)
        b = ContinuousEmotion(valence=0.1)
        assert a.distance(b) > 0

    def test_dominant_dimension(self):
        e = ContinuousEmotion(joy=0.9, calmness=0.1)
        assert e.dominant_dimension() == "joy"

    def test_intensity(self):
        e = ContinuousEmotion(valence=0.9, arousal=0.9)
        assert e.intensity() > 0.5

    def test_to_audio_parameters(self):
        e = ContinuousEmotion(valence=0.8, arousal=0.7)
        params = e.to_audio_parameters()
        assert "pitch_shift_semitones" in params
        assert "energy" in params
        assert 0.0 <= params["energy"] <= 1.0

    def test_named_presets(self):
        happy = ContinuousEmotion.from_named("happy")
        assert happy.joy > 0.5
        sad = ContinuousEmotion.from_named("sad")
        assert sad.sadness > 0.5

    def test_scale(self):
        e = ContinuousEmotion(valence=0.9, arousal=0.9)
        scaled = e.scale(0.0)
        assert scaled.valence == 0.5
        assert scaled.arousal == 0.5


class TestEmotionTransition:
    def test_linear_interpolation(self):
        a = ContinuousEmotion(valence=0.1)
        b = ContinuousEmotion(valence=0.9)
        t = EmotionTransition(a, b, curve=LINEAR, duration=1.0)
        mid = t.sample(0.5)
        assert abs(mid.valence - 0.5) < 1e-6

    def test_sigmoid_curve(self):
        a = ContinuousEmotion(valence=0.0)
        b = ContinuousEmotion(valence=1.0)
        t = EmotionTransition(a, b, curve=SIGMOID, duration=1.0)
        mid = t.sample(0.5)
        # Sigmoid at midpoint is 0.5.
        assert abs(mid.valence - 0.5) < 1e-6

    def test_cosine_curve(self):
        a = ContinuousEmotion(valence=0.0)
        b = ContinuousEmotion(valence=1.0)
        t = EmotionTransition(a, b, curve=COSINE, duration=1.0)
        mid = t.sample(0.5)
        # Cosine ease: (1 - cos(pi/2)) / 2 = 0.5
        assert abs(mid.valence - 0.5) < 1e-6

    def test_cubic_curve(self):
        a = ContinuousEmotion(valence=0.0)
        b = ContinuousEmotion(valence=1.0)
        t = EmotionTransition(a, b, curve=CUBIC, duration=1.0)
        mid = t.sample(0.5)
        # Cubic ease: 0.5^2 * (3 - 2*0.5) = 0.5
        assert abs(mid.valence - 0.5) < 1e-6

    def test_invalid_curve(self):
        with pytest.raises(ValueError):
            EmotionTransition(ContinuousEmotion(), ContinuousEmotion(), curve="bogus")

    def test_sample_curve_length(self):
        t = EmotionTransition(ContinuousEmotion(), ContinuousEmotion(valence=0.9), duration=1.0)
        samples = t.sample_curve(10)
        assert len(samples) == 10


class TestEmotionTimeline:
    def test_add_and_sample(self):
        timeline = EmotionTimeline()
        timeline.add_keyframe(0.0, ContinuousEmotion(valence=0.1))
        timeline.add_keyframe(1.0, ContinuousEmotion(valence=0.9))
        assert timeline.sample(0.0).valence == 0.1
        assert timeline.sample(1.0).valence == 0.9
        mid = timeline.sample(0.5)
        assert abs(mid.valence - 0.5) < 1e-6

    def test_looping(self):
        timeline = EmotionTimeline(loop=True)
        timeline.add_keyframe(0.0, ContinuousEmotion(valence=0.1))
        timeline.add_keyframe(1.0, ContinuousEmotion(valence=0.9))
        assert timeline.duration == 1.0
        wrapped = timeline.sample(1.5)
        assert abs(wrapped.valence - 0.5) < 1e-6

    def test_default_when_empty(self):
        timeline = EmotionTimeline()
        e = timeline.sample(10.0)
        assert e.valence == 0.5

    def test_to_dict_roundtrip(self):
        timeline = EmotionTimeline()
        timeline.add_keyframe(0.0, ContinuousEmotion(valence=0.2))
        timeline.add_keyframe(2.0, ContinuousEmotion(valence=0.8), curve=COSINE)
        data = timeline.to_dict()
        restored = EmotionTimeline.from_dict(data)
        assert restored.sample(0.0).valence == 0.2
        assert restored.sample(2.0).valence == 0.8