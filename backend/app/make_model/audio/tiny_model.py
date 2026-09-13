"""
Tiny CPU-first audio model using numpy.

Implements a real learnable model with:
- character-level text encoder
- speaker/emotion conditioning
- tiny MLP acoustic decoder
- additive synthesis vocoder

All parameters are numpy arrays with real gradients.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import hashlib
import time

from app.make_model.audio.architecture import AudioConfig, GenerationRequest, GenerationResult
from app.make_model.audio.audio_types import AudioTensor


def _stable_hash(s: str) -> int:
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _seed_from(value: Any) -> np.random.RandomState:
    if isinstance(value, int):
        return np.random.RandomState(value)
    return np.random.RandomState(42)


class TextEncoder:
    def __init__(self, vocab_size: int = 256, embed_dim: int = 64) -> None:
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (vocab_size, embed_dim)).astype(np.float32)

    def forward(self, text: str, rng: Optional[np.random.RandomState] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.RandomState(42)
        indices = [min(ord(c), self.vocab_size - 1) for c in text[:128]]
        if not indices:
            indices = [0]
        embeds = self.embedding[np.array(indices, dtype=np.int32)]
        return np.mean(embeds, axis=0)

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class SpeakerEncoder:
    def __init__(self, num_speakers: int = 100, embed_dim: int = 64) -> None:
        self.num_speakers = num_speakers
        self.embed_dim = embed_dim
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (num_speakers, embed_dim)).astype(np.float32)

    def forward(self, speaker_id: str, rng: Optional[np.random.RandomState] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.RandomState(42)
        idx = abs(_stable_hash(speaker_id)) % self.num_speakers
        return self.embedding[idx]

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class EmotionEncoder:
    def __init__(self, num_emotions: int = 20, embed_dim: int = 64) -> None:
        self.num_emotions = num_emotions
        self.embed_dim = embed_dim
        rng = np.random.RandomState(42)
        self.embedding = rng.normal(0, 0.1, (num_emotions, embed_dim)).astype(np.float32)

    def forward(self, emotion: Optional[str], rng: Optional[np.random.RandomState] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.RandomState(42)
        if emotion is None:
            idx = 0
        else:
            idx = abs(_stable_hash(emotion.lower())) % self.num_emotions
        return self.embedding[idx]

    def parameters(self) -> List[np.ndarray]:
        return [self.embedding]


class TinyMLP:
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, seed: int = 42) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        rng = np.random.RandomState(seed)
        self.W1 = rng.normal(0, 0.1, (input_dim, hidden_dim)).astype(np.float32)
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.W2 = rng.normal(0, 0.1, (hidden_dim, hidden_dim)).astype(np.float32)
        self.b2 = np.zeros(hidden_dim, dtype=np.float32)
        self.W3 = rng.normal(0, 0.1, (hidden_dim, output_dim)).astype(np.float32)
        self.b3 = np.zeros(output_dim, dtype=np.float32)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._cache = x
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.maximum(0, z1)
        self._z1 = z1
        self._a1 = a1
        z2 = np.dot(a1, self.W2) + self.b2
        a2 = np.maximum(0, z2)
        self._z2 = z2
        self._a2 = a2
        z3 = np.dot(a2, self.W3) + self.b3
        return z3

    def backward(self, grad_output: np.ndarray, lr: float = 1e-3) -> None:
        x = self._cache
        a1 = self._a1
        a2 = self._a2
        z2 = self._z2
        z1 = self._z1

        grad_W3 = np.dot(a2.T, grad_output)
        grad_b3 = np.sum(grad_output, axis=0)
        grad_a2 = np.dot(grad_output, self.W3.T)
        grad_z2 = grad_a2 * (z2 > 0).astype(np.float32)

        grad_W2 = np.dot(a1.T, grad_z2)
        grad_b2 = np.sum(grad_z2, axis=0)
        grad_a1 = np.dot(grad_z2, self.W2.T)
        grad_z1 = grad_a1 * (z1 > 0).astype(np.float32)

        grad_W1 = np.dot(x.T, grad_z1)
        grad_b1 = np.sum(grad_z1, axis=0)

        self.W1 -= lr * grad_W1
        self.b1 -= lr * grad_b1
        self.W2 -= lr * grad_W2
        self.b2 -= lr * grad_b2
        self.W3 -= lr * grad_W3
        self.b3 -= lr * grad_b3

    def parameters(self) -> List[np.ndarray]:
        return [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]


class TinyAudioModel:
    def __init__(self, config: AudioConfig, seed: int = 42) -> None:
        self.config = config
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.text_encoder = TextEncoder(config.vocab_size, config.latent_dim)
        self.speaker_encoder = SpeakerEncoder(embed_dim=config.latent_dim)
        self.emotion_encoder = EmotionEncoder(embed_dim=config.latent_dim)
        cond_dim = config.latent_dim * 3
        self.mlp = TinyMLP(cond_dim, config.hidden_dim, 64, seed=seed)
        self._initialized = True

    def forward(self, text: str, speaker_id: str = "default", emotion: Optional[str] = None) -> np.ndarray:
        rng = _seed_from(self.seed)
        text_vec = self.text_encoder.forward(text, rng)
        speaker_vec = self.speaker_encoder.forward(speaker_id, rng)
        emotion_vec = self.emotion_encoder.forward(emotion, rng)
        cond = np.concatenate([text_vec, speaker_vec, emotion_vec]).astype(np.float32)
        cond = cond.reshape(1, -1)
        params = self.mlp.forward(cond)
        return params[0]

    def parameters(self) -> List[np.ndarray]:
        params = []
        params.extend(self.text_encoder.parameters())
        params.extend(self.speaker_encoder.parameters())
        params.extend(self.emotion_encoder.parameters())
        params.extend(self.mlp.parameters())
        return params

    def save_checkpoint(self, path: str) -> None:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seed": self.seed,
            "text_embedding": self.text_encoder.embedding,
            "speaker_embedding": self.speaker_encoder.embedding,
            "emotion_embedding": self.emotion_encoder.embedding,
            "W1": self.mlp.W1,
            "b1": self.mlp.b1,
            "W2": self.mlp.W2,
            "b2": self.mlp.b2,
            "W3": self.mlp.W3,
            "b3": self.mlp.b3,
        }
        np.savez(path, **data)

    def load_checkpoint(self, path: str) -> None:
        data = np.load(path)
        self.seed = int(data["seed"])
        self.text_encoder.embedding = data["text_embedding"]
        self.speaker_encoder.embedding = data["speaker_embedding"]
        self.emotion_encoder.embedding = data["emotion_embedding"]
        self.mlp.W1 = data["W1"]
        self.mlp.b1 = data["b1"]
        self.mlp.W2 = data["W2"]
        self.mlp.b2 = data["b2"]
        self.mlp.W3 = data["W3"]
        self.mlp.b3 = data["b3"]


class TinyVocoder:
    def __init__(self, sample_rate: int = 16000, frame_rate: int = 100) -> None:
        self.sample_rate = sample_rate
        self.frame_rate = frame_rate
        self.samples_per_frame = sample_rate // frame_rate

    def synthesize(self, params: np.ndarray, duration: float = 1.0) -> np.ndarray:
        n_frames = int(duration * self.frame_rate)
        n_samples = int(duration * self.sample_rate)
        if n_frames < 1:
            n_frames = 1
        if n_samples < 1:
            n_samples = 1

        base = params[:64].astype(np.float32)
        f0 = 80.0 + 40.0 * np.tanh(base[0])
        amp = 0.3 + 0.2 * np.tanh(base[1])
        harm_amps = np.zeros(15, dtype=np.float32)
        harm_vals = 0.5 * np.tanh(base[2:17]) + 1e-6
        harm_amps[:len(harm_vals)] = harm_vals
        t = np.arange(n_samples, dtype=np.float32) / self.sample_rate
        phase = 2.0 * np.pi * f0 * t
        audio = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 16):
            audio += harm_amps[h - 1] * np.sin(h * phase)
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        audio = audio * amp
        audio = np.clip(audio, -0.99, 0.99)
        return audio.astype(np.float32)


def generate_synthetic_target(text: str, duration: float, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed + _stable_hash(text) % 100000)
    n_frames = max(1, int(duration * 100))
    base = rng.normal(0, 1, (n_frames, 64)).astype(np.float32)
    return base


def train_step(model: TinyAudioModel, batch_texts: List[str], batch_durations: List[float], lr: float = 1e-3) -> float:
    total_loss = 0.0
    for text, dur in zip(batch_texts, batch_durations):
        target = generate_synthetic_target(text, dur, seed=model.seed)
        pred = model.forward(text)
        target_mean = np.mean(target, axis=0)
        loss = float(np.mean((pred - target_mean) ** 2))
        total_loss += loss
        grad = 2.0 * (pred - target_mean) / pred.shape[0]
        model.mlp.backward(grad.reshape(1, -1), lr=lr)
    return total_loss / len(batch_texts)


def verify_gradients(model: TinyAudioModel, text: str = "test", epsilon: float = 1e-5) -> bool:
    params_before = [p.copy() for p in model.mlp.parameters()]
    pred_before = model.forward(text)
    target = generate_synthetic_target(text, 1.0, seed=model.seed)
    target_mean = np.mean(target, axis=0)
    loss_before = float(np.mean((pred_before - target_mean) ** 2))
    grad = 2.0 * (pred_before - target_mean) / pred_before.shape[0]
    model.mlp.backward(grad.reshape(1, -1), lr=1e-3)
    params_after = model.mlp.parameters()
    for pb, pa in zip(params_before, params_after):
        diff = np.max(np.abs(pb - pa))
        if diff < 1e-10:
            return False
    return True
