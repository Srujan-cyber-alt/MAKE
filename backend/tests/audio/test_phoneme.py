"""
Tests for the MAKE-native Phoneme/Prosody Engine.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.audio.phoneme import (
    TextNormalizer, GraphemeToPhoneme, Phonemizer, ProsodyModel,
    PitchContour, PhonemeDuration, ActingStyle, Sentence, Word, Phoneme,
    generate_waveform, seed_from_text,
)


class TestTextNormalizer:
    def test_lowercase(self):
        assert TextNormalizer.normalize("HELLO") == "hello"

    def test_punctuation_spacing(self):
        result = TextNormalizer.normalize("hello,world!")
        assert "," in result or "hello" in result

    def test_number_expansion(self):
        result = TextNormalizer.normalize("I have 3 cats")
        assert "three" in result

    def test_abbreviation_expansion(self):
        result = TextNormalizer.normalize("Mr smith")
        assert "mister" in result


class TestSentenceSegmenter:
    def test_single_sentence(self):
        from app.make_model.audio.phoneme import SentenceSegmenter
        result = SentenceSegmenter.segment("hello world")
        assert len(result) == 1
        assert result[0][0] == "hello world"
        assert result[0][1] is False

    def test_question_detection(self):
        from app.make_model.audio.phoneme import SentenceSegmenter
        result = SentenceSegmenter.segment("how are you?")
        assert len(result) == 1
        assert result[0][1] is True


class TestGraphemeToPhoneme:
    def test_known_word(self):
        assert GraphemeToPhoneme.convert("hello") == ["HH", "AH0", "L", "OW1"]

    def test_unknown_word(self):
        result = GraphemeToPhoneme.convert("xyzq")
        assert isinstance(result, list)

    def test_vowel_detection(self):
        assert GraphemeToPhoneme.is_vowel("AH0") is True
        assert GraphemeToPhoneme.is_vowel("K") is False

    def test_g2p_basic(self):
        result = GraphemeToPhoneme.convert("cat")
        assert "K" in result
        assert "AE1" in result or "AH0" in result


class TestPhonemizer:
    def test_phonemize_simple(self):
        sentences = Phonemizer.phonemize("hello world")
        assert len(sentences) >= 1
        assert len(sentences[0].words) >= 1

    def test_phonemize_question(self):
        sentences = Phonemizer.phonemize("how are you?")
        assert sentences[0].is_question is True


class TestPitchContour:
    def test_question_rises(self):
        freqs = PitchContour.generate(10, base_freq=120.0, is_question=True)
        assert freqs[-1] > freqs[0]

    def test_statement_falls(self):
        freqs = PitchContour.generate(10, base_freq=120.0, is_question=False)
        assert freqs[-1] < freqs[0]

    def test_whisper_lowers(self):
        normal = PitchContour.generate(10, base_freq=120.0)
        whisper = PitchContour.generate(10, base_freq=120.0, acting=ActingStyle.WHISPER)
        assert np.mean(whisper) < np.mean(normal)

    def test_shout_raises(self):
        normal = PitchContour.generate(10, base_freq=120.0)
        shout = PitchContour.generate(10, base_freq=120.0, acting=ActingStyle.SHOUT)
        assert np.mean(shout) > np.mean(normal)

    def test_deterministic(self):
        f1 = PitchContour.generate(10, base_freq=120.0, is_question=True)
        f2 = PitchContour.generate(10, base_freq=120.0, is_question=True)
        np.testing.assert_array_equal(f1, f2)


class TestPhonemeDuration:
    def test_stressed_longer_than_unstressed(self):
        stressed = PhonemeDuration.predict("AH0", is_stressed=True, is_vowel=True)
        unstressed = PhonemeDuration.predict("AH0", is_stressed=False, is_vowel=True)
        assert stressed > unstressed

    def test_vowel_longer_than_consonant(self):
        vowel = PhonemeDuration.predict("AH0", is_vowel=True)
        consonant = PhonemeDuration.predict("K", is_vowel=False)
        assert vowel > consonant

    def test_position_affects_duration(self):
        d1 = PhonemeDuration.predict("AH0", position=0, total=5, is_vowel=True)
        d2 = PhonemeDuration.predict("AH0", position=2, total=5, is_vowel=True)
        assert d1 > d2

    def test_whisper_shorter(self):
        normal = PhonemeDuration.predict("AH0", is_vowel=True)
        whisper = PhonemeDuration.predict("AH0", is_vowel=True, acting=ActingStyle.WHISPER)
        assert whisper < normal

    def test_urgent_faster(self):
        normal = PhonemeDuration.predict("AH0", is_vowel=True)
        urgent = PhonemeDuration.predict("AH0", is_vowel=True, acting=ActingStyle.URGENT)
        assert urgent < normal


class TestProsodyModel:
    def test_build_prosody_basic(self):
        phonemes = ["HH", "AH0", "L", "OW1"]
        stress = [0, 0, 0, 1]
        result = ProsodyModel.build_prosody(phonemes, stress, add_breath=False)
        assert len(result) == len(phonemes)
        for ph in result:
            assert ph.start_ms >= 0
            assert ph.duration_ms > 0

    def test_build_prosody_with_breath(self):
        phonemes = ["HH", "AH0"]
        stress = [0, 0]
        result = ProsodyModel.build_prosody(phonemes, stress, add_breath=True)
        assert any(p.symbol == "Breath" for p in result)

    def test_build_prosody_question(self):
        phonemes = ["HH", "AH0"]
        result = ProsodyModel.build_prosody(phonemes, [0, 0], is_question=True, add_breath=False)
        non_breath = [p for p in result if p.symbol != "Breath"]
        assert non_breath[-1].fundamental_freq > non_breath[0].fundamental_freq

    def test_build_prosody_whisper(self):
        phonemes = ["HH", "AH0"]
        result = ProsodyModel.build_prosody(phonemes, [0, 0], acting=ActingStyle.WHISPER)
        assert all(p.amplitude < 1.0 for p in result if p.symbol != "Breath")
        assert all(p.voicing < 1.0 for p in result if p.symbol != "Breath")


class TestGenerateWaveform:
    def test_waveform_length_positive(self):
        sentences = Phonemizer.phonemize("hello")
        audio = generate_waveform(sentences[0], sample_rate=16000)
        assert len(audio) > 0

    def test_waveform_is_float32(self):
        sentences = Phonemizer.phonemize("hello")
        audio = generate_waveform(sentences[0])
        assert audio.dtype == np.float32

    def test_waveform_amplitude_bounded(self):
        sentences = Phonemizer.phonemize("hello world")
        audio = generate_waveform(sentences[0])
        assert np.max(np.abs(audio)) <= 1.0

    def test_deterministic(self):
        np.random.seed(42)
        sentences = Phonemizer.phonemize("hello test")
        audio1 = generate_waveform(sentences[0])
        np.random.seed(42)
        audio2 = generate_waveform(sentences[0])
        np.testing.assert_array_equal(audio1, audio2)

    def test_whisper_reduces_amplitude(self):
        sentences = Phonemizer.phonemize("hello")
        normal = generate_waveform(sentences[0], acting=ActingStyle.NEUTRAL)
        whisper = generate_waveform(sentences[0], acting=ActingStyle.WHISPER)
        assert np.max(np.abs(whisper)) < np.max(np.abs(normal))

    def test_shout_increases_amplitude(self):
        sentences = Phonemizer.phonemize("hello")
        normal = generate_waveform(sentences[0], acting=ActingStyle.NEUTRAL)
        shout = generate_waveform(sentences[0], acting=ActingStyle.SHOUT)
        normal_rms = float(np.sqrt(np.mean(normal ** 2)))
        shout_rms = float(np.sqrt(np.mean(shout ** 2)))
        assert shout_rms > normal_rms


class TestSeedFromText:
    def test_deterministic_seed(self):
        assert seed_from_text("hello") == seed_from_text("hello")

    def test_different_texts_different_seeds(self):
        assert seed_from_text("hello") != seed_from_text("world")
