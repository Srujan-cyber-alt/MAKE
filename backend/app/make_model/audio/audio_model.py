"""
Enhanced Audio Model Layer.

Extends TinyMLP with:
- duration conditioning
- pitch conditioning
- energy conditioning
- emotion conditioning
- speaker conditioning
- style/acting conditioning
- room conditioning
- material conditioning
- spatial conditioning

All CPU-first numpy, real backprop, checkpointable, resumable.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import hashlib
from app.make_model.audio.architecture import AudioConfig
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder, TextEncoder, SpeakerEncoder, EmotionEncoder, _stable_hash


class EnhancedTextEncoder(TextEncoder):
    def __init__(self, vocab_size: int = 256, embed_dim: int = 64):
        super().__init__(vocab_size, embed_dim)

    def forward_full(self, text: str) -> np.ndarray:
        indices = [min(ord(c), self.vocab_size - 1) for c in text[:256]]
        if not indices:
            indices = [0]
        embeds = self.embedding[np.array(indices, dtype=np.int32)]
        if len(embeds) > 1:
            positions = np.arange(len(embeds)) / max(len(embeds), 1)
            weighted = embeds * (0.5 + 0.5 * positions[:, None])
            return np.mean(weighted, axis=0)
        return embeds[0]


class DurationEncoder:
    def __init__(self, embed_dim: int = 64) -> None:
        self.embed_dim = embed_dim

    def forward(self, duration: float) -> np.ndarray:
        norm = np.clip(duration / 10.0, 0, 1)
        vec = np.zeros(self.embed_dim, dtype=np.float32)
        for i in range(self.embed_dim):
            vec[i] = np.sin(norm * np.pi * (i + 1) / self.embed_dim)
        return vec

    def parameters(self) -> List[np.ndarray]:
        return []


class PitchEncoder:
    def __init__(self, embed_dim: int = 64) -> None:
        self.embed_dim = embed_dim

    def forward(self, pitch_hz: float) -> np.ndarray:
        norm = np.clip(np.log2(pitch_hz / 80.0) / 4.0, 0, 1)
        vec = np.zeros(self.embed_dim, dtype=np.float32)
        for i in range(self.embed_dim):
            vec[i] = np.sin(norm * np.pi * (i + 1) / self.embed_dim)
        return vec

    def parameters(self) -> List[np.ndarray]:
        return []


class StyleEncoder:
    STYLES = {
        "neutral": 0, "whisper": 1, "shout": 2, "hesitant": 3,
        "sarcastic": 4, "confident": 5, "nervous": 6, "intimate": 7,
        "authoritative": 8, "exhausted": 9, "crying": 10, "laughing": 11,
        "breathy": 12, "dramatic": 13, "urgent": 14, "calm": 15,
    }

    def __init__(self, num_styles: int = 16, embed_dim: int = 64) -> None:
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (num_styles, embed_dim)).astype(np.float32)
        self.num_styles = num_styles
        self.embed_dim = embed_dim

    def forward(self, style: Optional[str]) -> np.ndarray:
        if style is None or style not in self.STYLES:
            idx = self.STYLES["neutral"]
        else:
            idx = self.STYLES[style]
        return self.embedding[idx]

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class EnhancedAudioModel:
    def __init__(self, config: AudioConfig, seed: int = 42) -> None:
        self.config = config
        self.seed = seed
        latent = config.latent_dim
        self.text_encoder = EnhancedTextEncoder(config.vocab_size, latent)
        self.speaker_encoder = SpeakerEncoder(embed_dim=latent)
        self.emotion_encoder = EmotionEncoder(embed_dim=latent)
        self.duration_encoder = DurationEncoder(latent)
        self.pitch_encoder = PitchEncoder(latent)
        self.style_encoder = StyleEncoder(embed_dim=latent)
        self.room_encoder = RoomEncoder(latent)
        self.material_encoder = MaterialEncoder(latent)
        self.spatial_encoder = SpatialEncoder(latent)
        cond_dim = latent * 9
        from app.make_model.audio.tiny_model import TinyMLP
        self.mlp = TinyMLP(
            input_dim=cond_dim,
            hidden_dim=config.hidden_dim,
            output_dim=config.hidden_dim // 2,
            seed=seed,
        )
        self.vocoder = TinyVocoder(sample_rate=config.sample_rate)
        self._initialized = True

    def forward(
        self,
        text: str,
        speaker_id: str = "default",
        emotion: Optional[str] = None,
        duration: float = 2.0,
        pitch_hz: float = 120.0,
        style: Optional[str] = None,
        room_type: Optional[str] = None,
        material: Optional[str] = None,
        spatial_pos: Optional[Tuple[float, float, float]] = None,
    ) -> np.ndarray:
        t_vec = self.text_encoder.forward_full(text)
        s_vec = self.speaker_encoder.forward(speaker_id)
        e_vec = self.emotion_encoder.forward(emotion)
        d_vec = self.duration_encoder.forward(duration)
        p_vec = self.pitch_encoder.forward(pitch_hz)
        st_vec = self.style_encoder.forward(style)
        r_vec = self.room_encoder.forward(room_type)
        m_vec = self.material_encoder.forward(material)
        sp_vec = self.spatial_encoder.forward(spatial_pos)
        cond = np.concatenate([t_vec, s_vec, e_vec, d_vec, p_vec, st_vec, r_vec, m_vec, sp_vec])
        cond = cond.reshape(1, -1).astype(np.float32)
        params = self.mlp.forward(cond)
        return params[0]

    def synthesize(
        self, text: str, speaker_id: str = "default",
        emotion: Optional[str] = None, duration: float = 2.0,
        pitch_hz: float = 120.0, style: Optional[str] = None,
        room_type: Optional[str] = None, material: Optional[str] = None,
        spatial_pos: Optional[Tuple[float, float, float]] = None,
    ) -> np.ndarray:
        params = self.forward(
            text, speaker_id, emotion, duration, pitch_hz, style,
            room_type, material, spatial_pos,
        )
        return self.vocoder.synthesize(params, duration)

    def parameters(self) -> List[np.ndarray]:
        params = []
        params.extend(self.text_encoder.parameters())
        params.extend(self.speaker_encoder.parameters())
        params.extend(self.emotion_encoder.parameters())
        params.extend(self.style_encoder.parameters())
        params.extend(self.room_encoder.parameters())
        params.extend(self.material_encoder.parameters())
        params.extend(self.spatial_encoder.parameters())
        params.extend(self.mlp.parameters())
        params.extend(self.vocoder.parameters() if hasattr(self.vocoder, 'parameters') else [])
        return params

    def save_checkpoint(self, path: str) -> None:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seed": self.seed,
            "text_embedding": self.text_encoder.embedding,
            "speaker_embedding": self.speaker_encoder.embedding,
            "emotion_embedding": self.emotion_encoder.embedding,
            "style_embedding": self.style_encoder.embedding,
            "room_embedding": self.room_encoder.embedding,
            "material_embedding": self.material_encoder.embedding,
            "spatial_embedding": self.spatial_encoder.embedding,
            "W1": self.mlp.W1, "b1": self.mlp.b1,
            "W2": self.mlp.W2, "b2": self.mlp.b2,
            "W3": self.mlp.W3, "b3": self.mlp.b3,
        }
        np.savez(path, **data)

    def load_checkpoint(self, path: str) -> None:
        data = np.load(path)
        self.seed = int(data["seed"])
        self.text_encoder.embedding = data["text_embedding"]
        self.speaker_encoder.embedding = data["speaker_embedding"]
        self.emotion_encoder.embedding = data["emotion_embedding"]
        self.style_encoder.embedding = data["style_embedding"]
        self.room_encoder.embedding = data["room_embedding"]
        self.material_encoder.embedding = data["material_embedding"]
        self.spatial_encoder.embedding = data["spatial_embedding"]
        self.mlp.W1 = data["W1"]
        self.mlp.b1 = data["b1"]
        self.mlp.W2 = data["W2"]
        self.mlp.b2 = data["b2"]
        self.mlp.W3 = data["W3"]
        self.mlp.b3 = data["b3"]


class RoomEncoder:
    ROOMS = {
        "studio": 0, "bathroom": 1, "church": 2, "warehouse": 3,
        "car": 4, "street": 5, "forest": 6, "underwater": 7,
        "mountain": 8, "bedroom": 9, "cave": 10, "tunnel": 11,
        "theater": 12, "spaceship": 13, "concrete_bunker": 14,
        "metal_room": 15, "outdoor": 16, "carpeted": 17,
    }

    def __init__(self, embed_dim: int = 64) -> None:
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (len(self.ROOMS), embed_dim)).astype(np.float32)
        self.embed_dim = embed_dim

    def forward(self, room_type: Optional[str]) -> np.ndarray:
        if room_type is None or room_type not in self.ROOMS:
            idx = self.ROOMS["studio"]
        else:
            idx = self.ROOMS[room_type]
        return self.embedding[idx]

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class MaterialEncoder:
    MATERIALS = {
        "wood": 0, "metal": 1, "glass": 2, "plastic": 3,
        "stone": 4, "concrete": 5, "ceramic": 6, "rubber": 7,
        "fabric": 8, "water": 9, "paper": 10, "leather": 11,
        "sand": 12, "snow": 13, "ice": 14,
    }

    def __init__(self, embed_dim: int = 64) -> None:
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (len(self.MATERIALS), embed_dim)).astype(np.float32)
        self.embed_dim = embed_dim

    def forward(self, material: Optional[str]) -> np.ndarray:
        if material is None or material not in self.MATERIALS:
            idx = 0
        else:
            idx = self.MATERIALS[material]
        return self.embedding[idx]

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class SpatialEncoder:
    def __init__(self, embed_dim: int = 64) -> None:
        self.embed_dim = embed_dim

    def forward(self, pos: Optional[Tuple[float, float, float]]) -> np.ndarray:
        vec = np.zeros(self.embed_dim, dtype=np.float32)
        if pos is not None:
            for i in range(min(self.embed_dim, 3)):
                vec[i] = pos[i]
        return vec

    def parameters(self) -> List[np.ndarray]:
        return []


def train_enhanced_step(
    model: EnhancedAudioModel,
    batch_texts: List[str],
    batch_durations: List[float],
    lr: float = 1e-3,
) -> float:
    from app.make_model.audio.tiny_model import generate_synthetic_target
    total_loss = 0.0
    for text, dur in zip(batch_texts, batch_durations):
        target = generate_synthetic_target(text, dur, seed=model.seed)
        pred = model.forward(text, duration=dur)
        target_mean = np.mean(target, axis=0) if target.shape[0] > 0 else target
        if len(pred) > len(target_mean):
            target_mean = np.pad(target_mean, (0, len(pred) - len(target_mean)))
        elif len(pred) < len(target_mean):
            target_mean = target_mean[:len(pred)]
        loss = float(np.mean((pred - target_mean) ** 2))
        total_loss += loss
        grad = 2.0 * (pred - target_mean) / max(1, pred.shape[0])
        model.mlp.backward(grad.reshape(1, -1), lr=lr)
    return total_loss / len(batch_texts)
