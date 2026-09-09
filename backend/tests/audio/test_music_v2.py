"""Tests for Music Intelligence V2."""
import numpy as np
import pytest
from app.make_model.audio.music_v2 import (
    MusicIntelligence, MusicAnalysis, Chord, Section,
)


class TestMusicV2:
    @pytest.fixture
    def engine(self):
        return MusicIntelligence(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(16000) / 16000
        return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    def test_engine_creation(self, engine):
        assert engine.sample_rate == 16000

    def test_detect_bpm(self, engine, test_audio):
        bpm = engine.detect_bpm(test_audio)
        assert 40 <= bpm <= 300

    def test_detect_key(self, engine, test_audio):
        key = engine.detect_key(test_audio)
        assert key in MusicIntelligence.KEYS or key == "C"

    def test_detect_scale(self, engine, test_audio):
        scale = engine.detect_scale(test_audio)
        assert scale in MusicIntelligence.SCALES

    def test_chord_progression(self, engine, test_audio):
        chords = engine.extract_chord_progression(test_audio, 120, "C")
        assert len(chords) > 0
        assert all(isinstance(c, Chord) for c in chords)

    def test_sections(self, engine, test_audio):
        sections = engine.extract_sections(test_audio, 120)
        assert len(sections) > 0
        assert all(isinstance(s, Section) for s in sections)
        section_names = [s.name for s in sections]
        assert "intro" in section_names or "verse" in section_names

    def test_melody_extraction(self, engine, test_audio):
        notes = engine.extract_melody(test_audio)
        assert len(notes) > 0
        for note in notes:
            assert 50 < note < 2000

    def test_rhythm_extraction(self, engine, test_audio):
        rhythm = engine.extract_rhythm(test_audio)
        assert len(rhythm) > 0

    def test_full_analysis(self, engine, test_audio):
        analysis = engine.analyze(test_audio)
        assert isinstance(analysis, MusicAnalysis)
        assert analysis.bpm > 0
        assert len(analysis.key) > 0
        assert len(analysis.chord_progression) > 0
        assert len(analysis.sections) > 0
        assert len(analysis.melody_notes) > 0
        assert 0 <= analysis.overall_tension <= 1
        assert 0 <= analysis.overall_energy <= 1

    def test_generate_music(self, engine):
        audio = engine.generate_music(bpm=120, key="C", scale="major")
        assert len(audio) > 0
        assert np.max(np.abs(audio)) <= 0.99

    def test_music_continuity(self, engine):
        a1 = engine.analyze(engine.generate_music(120, "C"))
        a2 = engine.analyze(engine.generate_music(130, "G"))
        continuity = engine.music_continuity(a1, a2)
        assert "key_continuity" in continuity
        assert "bpm_continuity" in continuity
        assert "overall_continuity_score" in continuity

    def test_instruments_detected(self, engine, test_audio):
        analysis = engine.analyze(test_audio)
        assert len(analysis.instrumentation) > 0

    def test_dynamics_curve(self, engine, test_audio):
        analysis = engine.analyze(test_audio)
        assert len(analysis.dynamics_curve) > 0
