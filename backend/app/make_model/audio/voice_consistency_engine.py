"""
Voice consistency engine.

Guarantees that the same ``voice_id`` always produces recognisably the same
voice by caching genome-derived conditioning parameters and exposing a
``generate_conditioning`` helper that downstream generators can consume.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

import numpy as np

from app.make_model.audio.voice_genome import VoiceGenome
from app.make_model.audio.voice_embedding import VoiceEmbedding


class VoiceConsistencyEngine:
    """Ensures same voice_id produces consistent outputs."""

    def __init__(self, store: Optional["VoiceIdentityStore"] = None) -> None:
        from app.make_model.audio.voice_identity_store import VoiceIdentityStore

        self.store = store if store is not None else VoiceIdentityStore()
        self.embedding = VoiceEmbedding()
        self._cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Genome management
    # ------------------------------------------------------------------
    def register_voice(self, voice: VoiceGenome) -> VoiceGenome:
        return self.store.create(voice)

    def get_voice(self, voice_id: str) -> Optional[VoiceGenome]:
        return self.store.get(voice_id)

    def get_or_create_voice(self, voice_id: str, **defaults: Any) -> VoiceGenome:
        return self.store.get_or_create(voice_id, **defaults)

    def update_voice(self, voice_id: str, updates: Dict[str, Any]) -> Optional[VoiceGenome]:
        return self.store.update(voice_id, updates)

    def delete_voice(self, voice_id: str) -> bool:
        return self.store.delete(voice_id)

    def list_voices(self) -> list:
        return self.store.list_ids()

    # ------------------------------------------------------------------
    # Conditioning generation
    # ------------------------------------------------------------------
    def generate_conditioning(self, voice_id: str, emotion: Optional[str] = None) -> Dict[str, Any]:
        """Return a stable conditioning dict for the requested voice."""
        voice = self.get_or_create_voice(voice_id)
        cached = self._cache.get(voice_id)
        if cached is None:
            conditioning = self._build_conditioning(voice)
            self._cache[voice_id] = conditioning
            cached = conditioning
        # Emotion shifts energy / pitch slightly but keeps timbre stable.
        result = dict(cached)
        if emotion:
            result["emotion"] = emotion
            result.update(self._apply_emotion_shift(emotion, cached))
        result["voice_hash"] = voice.canonical_hash()
        result["embedding"] = self.embedding.embed(voice_id)
        return result

    def _build_conditioning(self, voice: VoiceGenome) -> Dict[str, Any]:
        return {
            "voice_id": voice.voice_id,
            "pitch": voice.pitch,
            "timbre": dict(voice.timbre),
            "resonance": voice.resonance,
            "formants": dict(voice.formants),
            "breathiness": voice.breathiness,
            "roughness": voice.roughness,
            "nasality": voice.nasality,
            "articulation": voice.articulation,
            "rhythm": voice.rhythm,
            "cadence": voice.cadence,
            "energy": voice.energy,
            "emotional_tendencies": dict(voice.emotional_tendencies),
            "age_representation": voice.age_representation,
        }

    def _apply_emotion_shift(self, emotion: str, base: Dict[str, Any]) -> Dict[str, float]:
        """Return small deterministic shifts keyed by emotion."""
        seed = int(hashlib.sha256(f"{emotion}:{base.get('voice_id', '')}".encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        shift: Dict[str, float] = {}
        # Energy and pitch are the main levers.
        if emotion in {"angry", "excited", "surprised"}:
            shift["energy"] = float(base.get("energy", 0.5) + rng.uniform(0.05, 0.15))
            shift["pitch"] = float(base.get("pitch", 220.0) + rng.uniform(5, 15))
        elif emotion in {"sad", "calm", "exhausted"}:
            shift["energy"] = float(base.get("energy", 0.5) - rng.uniform(0.05, 0.15))
            shift["pitch"] = float(base.get("pitch", 220.0) - rng.uniform(5, 15))
        else:
            shift["energy"] = float(base.get("energy", 0.5) + rng.uniform(-0.05, 0.05))
        return shift

    # ------------------------------------------------------------------
    # Consistency checks
    # ------------------------------------------------------------------
    def check_consistency(self, voice_id: str, samples: int = 3) -> Dict[str, Any]:
        """Generate multiple conditioning samples and report variance."""
        embeddings = [self.embedding.embed(voice_id) for _ in range(max(1, samples))]
        stack = np.stack(embeddings, axis=0)
        variance = float(np.var(stack, axis=0).mean())
        return {
            "voice_id": voice_id,
            "samples": samples,
            "embedding_variance": variance,
            "consistent": variance < 1e-6,
        }

    def similarity(self, voice_id_a: str, voice_id_b: str) -> float:
        return self.embedding.similarity(voice_id_a, voice_id_b)