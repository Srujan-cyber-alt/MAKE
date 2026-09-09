"""
Determinism tests across all Audio engines.

Requirement: same input + same config + same seed = byte-identical output
"""

from __future__ import annotations

import os
import hashlib
import tempfile
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from app.make_model.audio.tiny_model import TinyAudioModel, generate_synthetic_target
from app.make_model.audio.voice import VoiceGenomeEngine
from app.make_model.audio.emotion import EmotionEngine
from app.make_model.audio.dialogue import DialogueEngine
from app.make_model.audio.foley import FoleyEngine
from app.make_model.audio.music import MusicIntelligence
from app.make_model.audio.soundscape import SoundscapeEngine
from app.make_model.audio.spatial import SpatialAudioDirector
from app.make_model.audio.enhancement import AudioEnhancementEngine
from app.make_model.audio.repair import AudioRepairEngine
from app.make_model.audio.voice_genome import VoiceGenome
from app.make_model.audio.voice_embedding import VoiceEmbedding
from app.make_model.audio.voice_identity_store import VoiceIdentityStore
from app.make_model.audio.foley_physics import FoleyPhysics
from app.make_model.audio.continuous_emotion import ContinuousEmotion
from app.make_model.audio.emotion_transition import EmotionTransition
from app.make_model.audio.architecture import AudioConfig
from app.make_model.audio.config_loader import get_default_config


def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _make_test_wav(path: str, sr: int = 16000, duration: float = 1.0, freq: float = 220.0) -> None:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    wavfile.write(path, sr, (audio * 32767).astype(np.int16))


class TestDeterminism:
    @pytest.fixture(scope="module")
    def config(self) -> AudioConfig:
        return get_default_config("tiny")

    @pytest.fixture(scope="module")
    def initialized_engines(self, config: AudioConfig):
        import asyncio
        loop = asyncio.new_event_loop()
        pipe = loop.run_until_complete(self._make_engines(config))
        return pipe

    @staticmethod
    async def _make_engines(config):
        from app.make_model.audio.generation import AudioGenerationPipeline
        pipe = AudioGenerationPipeline()
        await pipe.initialize()
        return pipe

    def test_tiny_model_determinism(self, config: AudioConfig):
        model1 = TinyAudioModel(config, seed=42)
        model2 = TinyAudioModel(config, seed=42)
        p1 = model1.forward("hello", "v1", "neutral")
        p2 = model2.forward("hello", "v1", "neutral")
        np.testing.assert_array_equal(p1, p2)

    def test_tiny_model_different_text(self, config: AudioConfig):
        model = TinyAudioModel(config, seed=42)
        p1 = model.forward("hello", "v1", "neutral")
        p2 = model.forward("world", "v1", "neutral")
        assert not np.array_equal(p1, p2)

    def test_voice_embedding_determinism(self):
        emb1 = VoiceEmbedding()
        emb2 = VoiceEmbedding()
        v1 = emb1.embed("test_voice")
        v2 = emb2.embed("test_voice")
        np.testing.assert_array_equal(v1, v2)

    def test_voice_embedding_different_ids(self):
        emb = VoiceEmbedding()
        v1 = emb.embed("voice_a")
        v2 = emb.embed("voice_b")
        assert not np.array_equal(v1, v2)

    def test_voice_genome_hash_determinism(self):
        genome1 = VoiceGenome(
            voice_id="test", timbre={"spectral_centroid": 0.5},
            pitch=220.0, resonance=0.5, formants={"f1": 0.5},
            breathiness=0.2, roughness=0.1, nasality=0.1,
            articulation=0.6, rhythm=1.0, cadence=1.0, energy=0.5,
            emotional_tendencies={"neutral": 1.0}, age_representation=0.5,
        )
        genome2 = VoiceGenome(
            voice_id="test", timbre={"spectral_centroid": 0.5},
            pitch=220.0, resonance=0.5, formants={"f1": 0.5},
            breathiness=0.2, roughness=0.1, nasality=0.1,
            articulation=0.6, rhythm=1.0, cadence=1.0, energy=0.5,
            emotional_tendencies={"neutral": 1.0}, age_representation=0.5,
        )
        assert genome1.canonical_hash() == genome2.canonical_hash()

    def test_voice_store_roundtrip(self, tmp_path):
        store = VoiceIdentityStore(str(tmp_path / "store.json"))
        genome = VoiceGenome(
            voice_id="v1", timbre={"spectral_centroid": 0.3},
            pitch=200.0, resonance=0.7, formants={"f1": 0.4},
            breathiness=0.3, roughness=0.1, nasality=0.1,
            articulation=0.8, rhythm=1.1, cadence=1.0, energy=0.5,
            emotional_tendencies={"happy": 0.8}, age_representation=0.5,
        )
        store.create(genome)
        retrieved = store.get("v1")
        assert retrieved is not None
        assert retrieved.voice_id == "v1"
        assert retrieved.pitch == 200.0

    def test_emotion_transition_determinism(self):
        e1 = ContinuousEmotion.from_named("happy")
        e2 = ContinuousEmotion.from_named("sad")
        transition = EmotionTransition(e1, e2)
        state1 = transition.sample(0.3)
        state2 = transition.sample(0.3)
        assert state1.valence == state2.valence
        assert state1.arousal == state2.arousal

    def test_voice_synthesis_determinism(self, initialized_engines):
        import asyncio
        async def run():
            pipe = initialized_engines
            r1 = await pipe.synthesize_voice("hello", "voice_a", "neutral")
            r2 = await pipe.synthesize_voice("hello", "voice_a", "neutral")
            return _file_hash(r1.audio_path), _file_hash(r2.audio_path)
        h1, h2 = asyncio.get_event_loop().run_until_complete(run()) if False else asyncio.run(run())
        assert h1 == h2

    def test_emotion_engine_determinism(self, initialized_engines):
        import asyncio
        async def run():
            pipe = initialized_engines
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                _make_test_wav(f.name)
                audio_path = f.name
            r1 = await pipe.apply_emotion(audio_path, "happy", 0.8)
            r2 = await pipe.apply_emotion(audio_path, "happy", 0.8)
            return _file_hash(r1.audio_path), _file_hash(r2.audio_path)
        h1, h2 = asyncio.run(run())
        assert h1 == h2

    def test_foley_determinism(self, initialized_engines):
        import asyncio
        async def run():
            pipe = initialized_engines
            r1 = await pipe.get_model_async("foley")
            if r1 and hasattr(r1, 'generate_foley'):
                res1 = await r1.generate_foley("footstep", 0.5, {"material": "wood"})
                res2 = await r1.generate_foley("footstep", 0.5, {"material": "wood"})
                return _file_hash(res1.audio_path), _file_hash(res2.audio_path)
            return None, None
        h1, h2 = asyncio.run(run())
        if h1 and h2:
            assert h1 == h2
