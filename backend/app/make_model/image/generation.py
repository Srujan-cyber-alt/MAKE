"""MAKE Image Engine — Generation Engine.

Text-to-image, image-to-image, multi-reference generation,
resolution cascade, and detail refinement.
Uses PyTorch for real sampling when available.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAVE_TORCH = True
except Exception:
    torch = None  # type: ignore
    F = None  # type: ignore
    _HAVE_TORCH = False


@dataclass
class GenerationResult:
    image: Optional[np.ndarray] = None
    latents: Optional[np.ndarray] = None
    resolution: Tuple[int, int] = (256, 256)
    seed: int = 0
    steps: int = 20
    sampler: str = "euler"
    scheduler: str = "linear"
    cfg_scale: float = 3.0
    elapsed_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResolutionCascade:
    def __init__(self):
        self.stages = [
            {"short_side": 256, "name": "base"},
            {"short_side": 512, "name": "latent_refinement"},
            {"short_side": 1024, "name": "detail_refinement"},
            {"short_side": 2048, "name": "super_resolution"},
            {"short_side": 4096, "name": "final_reconstruction"},
        ]

    def stages_for(self, target_short_side: int) -> List[Dict[str, Any]]:
        return [s for s in self.stages if s["short_side"] <= target_short_side]

    def next_stage(self, current: int, target: int) -> Optional[Dict[str, Any]]:
        for s in self.stages:
            if current < s["short_side"] <= target:
                return s
        return None


def _set_seed(seed: int) -> None:
    if _HAVE_TORCH:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)


def _sample_noise(shape: Tuple[int, ...], seed: int, device: Any = None) -> Any:
    if _HAVE_TORCH:
        g = torch.Generator()
        g.manual_seed(seed)
        noise = torch.randn(shape, generator=g)
        if device is not None:
            noise = noise.to(device)
        return noise
    return np.random.randn(*shape).astype(np.float32)


def _flow_matching_step(model, z: Any, t: Any, conditioning: Any, cfg_scale: float, device: Any) -> Any:
    if _HAVE_TORCH:
        B = z.shape[0]
        t_batch = torch.full((B,), t, device=device, dtype=z.dtype)
        if conditioning is not None and "text_tok" in conditioning:
            text_tok = conditioning["text_tok"]
            if not isinstance(text_tok, torch.Tensor):
                text_tok = torch.from_numpy(np.asarray(text_tok)).to(device)
            if text_tok.ndim == 1:
                text_tok = text_tok.unsqueeze(0)
            if text_tok.shape[0] != B:
                text_tok = text_tok.repeat(B, 1)
        else:
            text_tok = torch.zeros((B, 16), device=device, dtype=torch.long)
        pred = model(z, t_batch, text_tok, conditioning=conditioning)
        if cfg_scale != 1.0 and conditioning is not None and "text_tok" in conditioning:
            pred_uncond = model(z, t_batch, torch.zeros_like(text_tok), conditioning=None)
            pred = pred_uncond + cfg_scale * (pred - pred_uncond)
        return pred
    return z


def _euler_sampling(model, shape: Tuple[int, ...], conditioning: Any, cfg: Any, seed: int, steps: int, device: Any) -> Any:
    z = _sample_noise(shape, seed, device)
    dt = 1.0 / steps
    for i in range(steps):
        t = i / steps
        pred = _flow_matching_step(model, z, t, conditioning, cfg.cfg_scale, device)
        if _HAVE_TORCH and isinstance(z, torch.Tensor):
            z = z + dt * pred
        else:
            z = z + dt * pred
    return z


class GenerationEngine:
    def __init__(self, model: Any = None):
        self.model = model
        self.cascade = ResolutionCascade()

    def _get_device(self) -> Any:
        if _HAVE_TORCH and torch.cuda.is_available():
            return torch.device("cuda")
        if _HAVE_TORCH:
            return torch.device("cpu")
        return None

    def _call_model(self, z, t, text_tok, conditioning, device):
        if _HAVE_TORCH and hasattr(self.model, 'to_torch'):
            try:
                torch_model = self.model.to_torch()
                if device is not None:
                    torch_model = torch_model.to(device)
                if not isinstance(z, torch.Tensor):
                    z = torch.from_numpy(z).to(device)
                if not isinstance(t, torch.Tensor):
                    t = torch.full((z.shape[0],), float(t), device=device, dtype=z.dtype)
                if not isinstance(text_tok, torch.Tensor):
                    text_tok = torch.from_numpy(np.asarray(text_tok)).to(device)
                if text_tok.ndim == 1:
                    text_tok = text_tok.unsqueeze(0)
                pred = torch_model(z, t, text_tok, conditioning=conditioning)
                return pred
            except Exception:
                pass
        return self.model.forward(z, t, text_tok, conditioning=conditioning)

    def text_to_image(self, prompt: str, conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0) -> GenerationResult:
        t0 = time.time()
        if self.model is None:
            return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side))

        _set_seed(seed)
        device = self._get_device()

        latent_side = max(16, short_side // 8)
        shape = (1, self.model.cfg.image_channels, latent_side, latent_side)
        cond = conditioning if conditioning is not None else {}
        if isinstance(cond, dict):
            cond = cond.copy()
        else:
            cond = {}

        if "text_tok" not in cond:
            tokens = np.array([ord(c) % 4096 for c in (prompt or "")], dtype=np.int64)[:16]
            tokens = np.pad(tokens, (0, max(0, 16 - tokens.size)))
            cond["text_tok"] = tokens

        z = _sample_noise(shape, seed, device)
        dt = 1.0 / steps
        for i in range(steps):
            t_val = i / steps
            pred = self._call_model(z, t_val, cond.get("text_tok"), cond, device)
            if _HAVE_TORCH and isinstance(pred, torch.Tensor):
                pred = pred.detach().cpu().numpy()
            if pred.shape[1] != z.shape[1]:
                pred = pred[:, :z.shape[1], :, :]
            if _HAVE_TORCH and isinstance(z, torch.Tensor):
                z = z + dt * torch.from_numpy(pred).to(z.device)
            else:
                z = z + dt * pred

        if _HAVE_TORCH and isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()

        upscaled = np.repeat(z, 8, axis=2)
        upscaled = np.repeat(upscaled, 8, axis=3)
        image = np.tanh(upscaled) * 0.5 + 0.5
        image = image.clip(0, 1)

        return GenerationResult(
            image=image,
            latents=z,
            resolution=(image.shape[3], image.shape[2]),
            seed=seed,
            steps=steps,
            sampler="euler",
            scheduler="linear",
            cfg_scale=cfg_scale,
            elapsed_seconds=time.time() - t0,
            metadata={"prompt": prompt, "latent_side": latent_side},
        )

    def image_to_image(self, image: np.ndarray, conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0, strength: float = 0.8) -> GenerationResult:
        t0 = time.time()
        if self.model is None:
            return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side), metadata={"strength": strength})

        _set_seed(seed)
        device = self._get_device()
        model = self.model
        if _HAVE_TORCH and hasattr(model, 'to_torch'):
            model = model.to_torch()
            if device is not None:
                model = model.to(device)

        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        x = x.transpose(0, 3, 1, 2) if x.shape[-1] == 3 else x
        latent_side = max(16, short_side // 8)
        downsampled = x[:, :, ::8, ::8]
        if downsampled.shape[2] != latent_side or downsampled.shape[3] != latent_side:
            downsampled = np.repeat(downsampled, math.ceil(latent_side / max(1, downsampled.shape[2])), axis=2)
            downsampled = np.repeat(downsampled, math.ceil(latent_side / max(1, downsampled.shape[3])), axis=3)
            downsampled = downsampled[:, :, :latent_side, :latent_side]

        noise = _sample_noise((1, getattr(model.cfg, 'image_channels', 3), latent_side, latent_side), seed, device)
        if _HAVE_TORCH and isinstance(noise, torch.Tensor):
            downsampled_t = torch.from_numpy(downsampled).to(device)
            z = (1 - strength) * downsampled_t + strength * noise
        else:
            z = (1 - strength) * downsampled + strength * noise

        cond = conditioning if conditioning is not None else {}
        if isinstance(cond, dict):
            cond = cond.copy()
        else:
            cond = {}
        if "text_tok" not in cond:
            tokens = np.zeros((1, 16), dtype=np.int64)
            cond["text_tok"] = tokens

        z = _euler_sampling(model, z.shape, cond, type('Cfg', (), {'cfg_scale': cfg_scale})(), seed, steps, device)
        if _HAVE_TORCH and isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()

        upscaled = np.repeat(z, 8, axis=2)
        upscaled = np.repeat(upscaled, 8, axis=3)
        image = np.tanh(upscaled) * 0.5 + 0.5
        image = image.clip(0, 1)

        return GenerationResult(
            image=image,
            latents=z,
            resolution=(image.shape[3], image.shape[2]),
            seed=seed,
            steps=steps,
            sampler="euler",
            scheduler="linear",
            cfg_scale=cfg_scale,
            elapsed_seconds=time.time() - t0,
            metadata={"strength": strength},
        )

    def multi_reference_to_image(self, references: List[np.ndarray], conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0) -> GenerationResult:
        t0 = time.time()
        if self.model is None:
            return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side), metadata={"num_references": len(references)})

        _set_seed(seed)
        device = self._get_device()
        model = self.model
        if _HAVE_TORCH and hasattr(model, 'to_torch'):
            model = model.to_torch()
            if device is not None:
                model = model.to(device)

        latent_side = max(16, short_side // 8)
        shape = (1, getattr(model.cfg, 'image_channels', 3), latent_side, latent_side)
        cond = conditioning if conditioning is not None else {}
        if isinstance(cond, dict):
            cond = cond.copy()
        else:
            cond = {}
        if "text_tok" not in cond:
            tokens = np.zeros((1, 16), dtype=np.int64)
            cond["text_tok"] = tokens
        if references and "image_emb" not in cond:
            ref = np.asarray(references[0], dtype=np.float32)
            if ref.ndim == 3:
                ref = ref[None]
            pooled = ref.mean(axis=(2, 3))
            cond["image_emb"] = pooled

        z = _euler_sampling(model, shape, cond, type('Cfg', (), {'cfg_scale': cfg_scale})(), seed, steps, device)
        if _HAVE_TORCH and isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()

        upscaled = np.repeat(z, 8, axis=2)
        upscaled = np.repeat(upscaled, 8, axis=3)
        image = np.tanh(upscaled) * 0.5 + 0.5
        image = image.clip(0, 1)

        return GenerationResult(
            image=image,
            latents=z,
            resolution=(image.shape[3], image.shape[2]),
            seed=seed,
            steps=steps,
            sampler="euler",
            scheduler="linear",
            cfg_scale=cfg_scale,
            elapsed_seconds=time.time() - t0,
            metadata={"num_references": len(references)},
        )

    def run_cascade(self, prompt: str, conditioning: Any, cfg: Any, target_short_side: int = 1024, seed: int = 42) -> GenerationResult:
        stages = self.cascade.stages_for(target_short_side)
        current: Optional[GenerationResult] = None
        for stage in stages:
            current = self.text_to_image(prompt, conditioning, cfg, seed=seed, short_side=stage["short_side"], steps=max(10, 20 // len(stages)))
            if current and current.image is not None:
                conditioning = {"text_tok": conditioning.get("text_tok") if isinstance(conditioning, dict) else None}
        if current is None:
            current = self.text_to_image(prompt, conditioning, cfg, seed=seed, short_side=256, steps=20)
        return current or GenerationResult(seed=seed, steps=20, sampler="euler", scheduler="linear", cfg_scale=3.0, resolution=(256, 256))


__all__ = [
    "GenerationResult",
    "ResolutionCascade",
    "GenerationEngine",
]
