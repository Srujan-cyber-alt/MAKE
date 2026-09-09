"""Tests for music intelligence v2 and music memory."""

import pytest

from app.make_model.audio.music_intelligence_v2 import (
    MusicIntelligence,
    Meter,
    Key,
    Harmony,
    Melody,
    RhythmPattern,
    Instrumentation,
)
from app.make_model.audio.music_memory import MusicMemory, MusicalMotif


class TestMusicIntelligence:
    def test_defaults(self):
        music = MusicIntelligence()
        assert music.tempo == 120.0
        assert music.meter == Meter.FOUR_FOUR
        assert music.key == Key.C_MAJOR

    def test_beat_duration(self):
        music = MusicIntelligence(tempo=120.0)
        assert abs(music.beat_duration() - 0.5) < 1e-6

    def test_bars(self):
        music = MusicIntelligence(tempo=120.0, duration=8.0)
        assert music.bars() == 4

    def test_midi_notes(self):
        music = MusicIntelligence()
        notes = music.midi_notes()
        assert len(notes) == 7

    def test_to_dict_roundtrip(self):
        music = MusicIntelligence(
            tempo=140.0,
            harmony=Harmony(progression=["C", "Am", "F", "G"]),
            melody=Melody(motif=[60, 64, 67]),
            instrumentation=Instrumentation(instruments=["piano", "bass"]),
        )
        data = music.to_dict()
        restored = MusicIntelligence.from_dict(data)
        assert restored.tempo == 140.0
        assert restored.harmony.progression == ["C", "Am", "F", "G"]

    def test_meter_three_four(self):
        music = MusicIntelligence(meter=Meter.THREE_FOUR, tempo=120.0)
        assert music.meter == Meter.THREE_FOUR

    def test_minor_key(self):
        music = MusicIntelligence(key=Key.A_MINOR)
        notes = music.midi_notes()
        assert len(notes) == 7

    def test_energy(self):
        music = MusicIntelligence(energy=0.9)
        assert music.energy == 0.9

    def test_rhythm(self):
        music = MusicIntelligence(rhythm=RhythmPattern(pattern=[1.0, 0.5, 0.5]))
        assert music.rhythm.pattern == [1.0, 0.5, 0.5]


class TestMusicMemory:
    def test_set_dna(self):
        mem = MusicMemory("m1")
        dna = MusicIntelligence(tempo=100.0)
        mem.set_dna(dna)
        assert mem.get_dna() is not None
        assert mem.get_dna().tempo == 100.0

    def test_add_motif(self):
        mem = MusicMemory("m1")
        motif = MusicalMotif(motif_id="motif1", notes=[60, 64, 67])
        mem.add_motif(motif)
        assert mem.get_motif("motif1") is not None

    def test_remove_motif(self):
        mem = MusicMemory("m1")
        motif = MusicalMotif(motif_id="motif1")
        mem.add_motif(motif)
        assert mem.remove_motif("motif1") is True
        assert mem.get_motif("motif1") is None

    def test_find_motifs_by_notes(self):
        mem = MusicMemory("m1")
        mem.add_motif(MusicalMotif(motif_id="m1", notes=[60, 64, 67]))
        mem.add_motif(MusicalMotif(motif_id="m2", notes=[70, 74, 77]))
        found = mem.find_motifs_by_notes([60, 64])
        assert [m.motif_id for m in found] == ["m1"]

    def test_add_cue(self):
        mem = MusicMemory("m1")
        cue = mem.add_cue({"title": "Cue 1"})
        assert cue["title"] == "Cue 1"

    def test_to_dict_roundtrip(self):
        mem = MusicMemory("m1")
        mem.set_dna(MusicIntelligence(tempo=110.0))
        mem.add_motif(MusicalMotif(motif_id="motif1", notes=[60, 64]))
        data = mem.to_dict()
        restored = MusicMemory.from_dict(data)
        assert restored.get_dna() is not None
        assert restored.get_motif("motif1") is not None

    def test_identity_hash(self):
        mem = MusicMemory("m1")
        h1 = mem.identity_hash()
        mem.set_dna(MusicIntelligence(tempo=120.0))
        h2 = mem.identity_hash()
        assert isinstance(h1, str) and len(h1) > 0
        assert h1 != h2