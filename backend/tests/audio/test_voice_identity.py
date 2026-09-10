"""Tests for Voice Identity Engine."""
import numpy as np
import pytest
from app.make_model.audio.voice_identity import VoiceIdentityEngine, VoiceGenome


class TestVoiceIdentity:
    def test_create_voice(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1", reference_texts=["hello world", "how are you"])
        assert isinstance(genome, VoiceGenome)
        assert genome.speaker_id == "speaker1"
        assert genome.version == 1
        assert genome.embedding.shape == (128,)
        assert len(genome.genome_id) == 16

    def test_persistent_voice_genome(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1", reference_texts=["test"])
        engine2 = VoiceIdentityEngine(128)
        data = engine.serialize()
        engine2.deserialize(data)
        loaded = engine2.get_voice(genome.genome_id)
        assert loaded is not None
        assert loaded.speaker_id == "speaker1"
        assert loaded.version == genome.version
        assert np.allclose(loaded.embedding, genome.embedding)

    def test_get_voice(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("test_speaker")
        retrieved = engine.get_voice(genome.genome_id)
        assert retrieved == genome

    def test_get_voice_not_found(self):
        engine = VoiceIdentityEngine(128)
        assert engine.get_voice("nonexistent") is None

    def test_branch_voice(self):
        engine = VoiceIdentityEngine(128)
        parent = engine.create_voice("speaker1", reference_texts=["original"])
        child = engine.branch_voice(parent.genome_id, "speaker1", reference_texts=["new sample"], strength=0.8)
        assert child.parent_genome_id == parent.genome_id
        assert child.version == 2
        assert len(child.reference_hashes) >= len(parent.reference_hashes)

    def test_detect_drift(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1", reference_texts=["hello"])
        same_embedding = genome.embedding.copy()
        drift, is_drift = engine.detect_drift(genome.genome_id, same_embedding)
        assert drift < 0.01
        assert is_drift is False

    def test_detect_significant_drift(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1", reference_texts=["hello"])
        different = np.random.RandomState(999).normal(0, 1, 128).astype(np.float32)
        different = different / (np.linalg.norm(different) + 1e-10)
        drift, is_drift = engine.detect_drift(genome.genome_id, different)
        assert is_drift is True

    def test_consistency_check(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1")
        emb1 = genome.embedding.copy()
        emb2 = genome.embedding.copy()
        consistency = engine.check_consistency([emb1, emb2])
        assert consistency > 0.99

    def test_rollback(self):
        engine = VoiceIdentityEngine(128)
        g1 = engine.create_voice("speaker1", reference_texts=["v1"])
        g2 = engine.branch_voice(g1.genome_id, "speaker1", reference_texts=["v2"])
        rolled_back = engine.rollback("speaker1", to_version=1)
        assert rolled_back is not None
        assert rolled_back.version <= 1

    def test_history(self):
        engine = VoiceIdentityEngine(128)
        g1 = engine.create_voice("speaker1", reference_texts=["v1"])
        engine.branch_voice(g1.genome_id, "speaker1", reference_texts=["v2"])
        history = engine.get_history("speaker1")
        assert len(history) >= 1
        history_sorted = sorted(history, key=lambda g: g.version)
        assert history_sorted == history

    def test_multi_reference_identity(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.multi_reference_identity("speaker1", [
            (["hello world"], 0.7),
            (["how are you"], 0.3),
        ])
        assert genome.embedding.shape == (128,)
        assert genome.provenance["creation_method"] == "multi_reference_blend"
        assert genome.provenance["reference_count"] == 2

    def test_identity_preservation_across_edits(self):
        engine = VoiceIdentityEngine(128)
        genome = engine.create_voice("speaker1", reference_texts=["original text"])
        emb1 = genome.embedding.copy()
        edited_emb = emb1 * 0.95 + genome.embedding * 0.05
        edited_emb = edited_emb / (np.linalg.norm(edited_emb) + 1e-10)
        drift, is_drift = engine.detect_drift(genome.genome_id, edited_emb, threshold=0.1)
        assert drift < 0.1

    def test_get_active_voice(self):
        engine = VoiceIdentityEngine(128)
        g1 = engine.create_voice("speaker1")
        engine.branch_voice(g1.genome_id, "speaker1")
        active = engine.get_active_voice("speaker1")
        assert active is not None
        assert active.version == 2
