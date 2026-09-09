"""Tests for voice identity modules (VoiceGenome, VoiceEmbedding, VoiceIdentityStore, VoiceConsistencyEngine)."""

import os
import tempfile
import time

import numpy as np
import pytest

from app.make_model.audio.voice_genome import VoiceGenome
from app.make_model.audio.voice_embedding import VoiceEmbedding
from app.make_model.audio.voice_identity_store import VoiceIdentityStore
from app.make_model.audio.voice_consistency_engine import VoiceConsistencyEngine


class TestVoiceGenome:
    def test_to_dict_roundtrip(self):
        genome = VoiceGenome(
            voice_id="v1",
            pitch=220.0,
            timbre={"spectral_centroid": 0.5},
            formants={"f1": 0.4},
            emotional_tendencies={"happy": 0.7},
        )
        data = genome.to_dict()
        assert data["voice_id"] == "v1"
        assert data["pitch"] == 220.0
        restored = VoiceGenome.from_dict(data)
        assert restored.voice_id == genome.voice_id
        assert restored.pitch == genome.pitch
        assert restored.timbre == genome.timbre

    def test_canonical_hash_stable(self):
        genome = VoiceGenome(voice_id="v1", pitch=200.0)
        h1 = genome.canonical_hash()
        genome.pitch = 220.0
        genome.updated_at = time.time()
        # Same voice_id + same pitch => same hash
        genome.pitch = 200.0
        h2 = genome.canonical_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_copy_independent(self):
        genome = VoiceGenome(voice_id="v1", pitch=200.0)
        clone = genome.copy()
        clone.pitch = 300.0
        assert genome.pitch == 200.0
        assert clone.pitch == 300.0

    def test_similarity(self):
        a = VoiceGenome(voice_id="a", pitch=200.0, resonance=0.5)
        b = VoiceGenome(voice_id="b", pitch=210.0, resonance=0.5)
        c = VoiceGenome(voice_id="c", pitch=400.0, resonance=0.1)
        assert a.similarity(b) > a.similarity(c)


class TestVoiceEmbedding:
    def test_deterministic(self):
        emb = VoiceEmbedding(dim=64)
        e1 = emb.embed("voice_1")
        e2 = emb.embed("voice_1")
        assert np.allclose(e1, e2)

    def test_different_voives_different(self):
        emb = VoiceEmbedding(dim=64)
        e1 = emb.embed("voice_1")
        e2 = emb.embed("voice_2")
        assert not np.allclose(e1, e2)

    def test_unit_norm(self):
        emb = VoiceEmbedding(dim=32)
        e = emb.embed("voice_1")
        assert abs(float(np.linalg.norm(e)) - 1.0) < 1e-5

    def test_similarity_symmetric(self):
        emb = VoiceEmbedding(dim=32)
        s1 = emb.similarity("a", "b")
        s2 = emb.similarity("b", "a")
        assert s1 == s2

    def test_distance_nonneg(self):
        emb = VoiceEmbedding(dim=16)
        assert emb.distance("a", "b") >= 0.0


class TestVoiceIdentityStore:
    def test_create_and_get(self, tmp_path):
        store = VoiceIdentityStore(str(tmp_path / "voices.json"))
        genome = VoiceGenome(voice_id="v1", pitch=220.0)
        store.create(genome)
        fetched = store.get("v1")
        assert fetched is not None
        assert fetched.pitch == 220.0

    def test_update(self, tmp_path):
        store = VoiceIdentityStore(str(tmp_path / "voices.json"))
        store.create(VoiceGenome(voice_id="v1", pitch=200.0))
        store.update("v1", {"pitch": 250.0})
        fetched = store.get("v1")
        assert fetched.pitch == 250.0

    def test_delete(self, tmp_path):
        store = VoiceIdentityStore(str(tmp_path / "voices.json"))
        store.create(VoiceGenome(voice_id="v1"))
        assert store.delete("v1") is True
        assert store.get("v1") is None
        assert store.delete("v1") is False

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "voices.json")
        store = VoiceIdentityStore(path)
        store.create(VoiceGenome(voice_id="v1"))
        store2 = VoiceIdentityStore(path)
        assert store2.get("v1") is not None

    def test_list_and_contains(self, tmp_path):
        store = VoiceIdentityStore(str(tmp_path / "voices.json"))
        store.create(VoiceGenome(voice_id="v1"))
        store.create(VoiceGenome(voice_id="v2"))
        assert "v1" in store
        assert "v2" in store
        assert "v3" not in store
        assert set(store.list_ids()) == {"v1", "v2"}


class TestVoiceConsistencyEngine:
    def test_same_voice_same_conditioning(self, tmp_path):
        engine = VoiceConsistencyEngine(VoiceIdentityStore(str(tmp_path / "vc.json")))
        c1 = engine.generate_conditioning("voice_A")
        c2 = engine.generate_conditioning("voice_A")
        assert c1["pitch"] == c2["pitch"]
        assert c1["voice_hash"] == c2["voice_hash"]

    def test_different_voices_different_hash(self, tmp_path):
        engine = VoiceConsistencyEngine(VoiceIdentityStore(str(tmp_path / "vc2.json")))
        c1 = engine.generate_conditioning("voice_A")
        c2 = engine.generate_conditioning("voice_B")
        assert c1["voice_hash"] != c2["voice_hash"]

    def test_consistency_check(self, tmp_path):
        engine = VoiceConsistencyEngine(VoiceIdentityStore(str(tmp_path / "vc3.json")))
        report = engine.check_consistency("voice_A", samples=5)
        assert report["consistent"] is True
        assert report["embedding_variance"] < 1e-6

    def test_emotion_shift(self, tmp_path):
        engine = VoiceConsistencyEngine(VoiceIdentityStore(str(tmp_path / "vc4.json")))
        base = engine.generate_conditioning("voice_A")
        angry = engine.generate_conditioning("voice_A", emotion="angry")
        assert angry["emotion"] == "angry"
        # Angry should raise energy relative to base.
        assert angry.get("energy", 0) >= base.get("energy", 0)