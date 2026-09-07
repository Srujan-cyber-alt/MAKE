"""
NumpyUNet: a tiny UNet-style denoising network in pure NumPy.

Design constraints (CPU, 11 GiB RAM, no PyTorch):
  - 32x32 native resolution only (square images, 3 channels)
  - 8 / 16 / 32 channel widths to keep params under ~250K
  - conv2d implemented as im2col + matmul
  - GroupNorm via channel-wise mean / var
  - sinusoidal timestep embedding
  - class-free text conditioning: hashed-prompt integer embedding

This is a real neural network that can be trained and that actually
denoises. It will not produce photorealistic 1024x1024 images; that
is compute-limited and reported honestly.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Tuple, List, Optional

import numpy as np


def _sinusoidal_embedding(t: np.ndarray, dim: int) -> np.ndarray:
    """Standard transformer-style sinusoidal embedding. t in [0, T)."""
    half = dim // 2
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(1, half - 1))
    args = t.astype(np.float32)[:, None] * freqs[None, :]
    emb = np.concatenate([np.sin(args), np.cos(args)], axis=1)
    if dim % 2 == 1:
        emb = np.concatenate([emb, np.zeros((emb.shape[0], 1), dtype=np.float32)], axis=1)
    return emb


def _prompt_embedding(prompt: str, dim: int) -> np.ndarray:
    """Deterministic, prompt-conditioned 1-D embedding.

    Hashes the prompt, seeds a small RNG, and returns a fixed-dim vector.
    Returns the zero vector for empty prompts so unconditional sampling works.
    """
    if not prompt:
        return np.zeros((dim,), dtype=np.float32)
    h = hashlib.sha256(prompt.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big") & 0x7FFFFFFF
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= max(1e-6, np.linalg.norm(v))
    return v


@dataclass
class NumpyUNetConfig:
    image_size: int = 32
    in_channels: int = 3
    base_channels: int = 32
    channel_mults: Tuple[int, ...] = (1,)
    num_res_blocks: int = 1
    text_dim: int = 32
    time_dim: int = 64
    num_timesteps: int = 200
    arch_version: str = "make-image-cpu-unet-v1"
    notes: str = "Pure-NumPy CPU UNet denoiser. 32x32 native. No GPU."

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NumpyUNetConfig":
        d = dict(d)
        cm = d.get("channel_mults", (1, 2))
        d["channel_mults"] = tuple(int(x) for x in cm)
        return cls(**d)

    def channels_at_level(self, level: int) -> int:
        return self.base_channels * self.channel_mults[level]


def _im2col(x: np.ndarray, kh: int, kw: int, pad: int = 0) -> np.ndarray:
    """Convert (B, C, H, W) into (B, C*kh*kw, L) columns."""
    B, C, H, W = x.shape
    if pad > 0:
        x = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode="constant")
        H2, W2 = H + 2 * pad, W + 2 * pad
    else:
        H2, W2 = H, W
    out_h = H2 - kh + 1
    out_w = W2 - kw + 1
    cols = np.zeros((B, C, kh, kw, out_h, out_w), dtype=x.dtype)
    for i in range(kh):
        for j in range(kw):
            cols[:, :, i, j, :, :] = x[:, :, i:i + out_h, j:j + out_w]
    return cols.reshape(B, C * kh * kw, out_h * out_w)


def _col2im(cols: np.ndarray, x_shape: Tuple[int, int, int, int], kh: int, kw: int,
            pad: int = 0) -> np.ndarray:
    """Inverse of _im2col (no overlap handling — only valid when stride==1, no overlap)."""
    B, C, H, W = x_shape
    H2 = H + 2 * pad
    W2 = W + 2 * pad
    out_h = H2 - kh + 1
    out_w = W2 - kw + 1
    cols = cols.reshape(B, C, kh, kw, out_h, out_w)
    x = np.zeros((B, C, H2, W2), dtype=cols.dtype)
    for i in range(kh):
        for j in range(kw):
            x[:, :, i:i + out_h, j:j + out_w] += cols[:, :, i, j, :, :]
    if pad > 0:
        return x[:, :, pad:-pad, pad:-pad]
    return x


def conv2d_forward(x: np.ndarray, w: np.ndarray, b: np.ndarray, pad: int = 0) -> np.ndarray:
    """x: (B, C_in, H, W)  w: (C_out, C_in, kh, kw)  b: (C_out,)"""
    B, _, H, W = x.shape
    C_out = w.shape[0]
    kh, kw = w.shape[2], w.shape[3]
    cols = _im2col(x, kh, kw, pad=pad)
    w_flat = w.reshape(C_out, -1)
    out = w_flat @ cols
    out = out + b[:, None]
    out_h = H + 2 * pad - kh + 1
    out_w = W + 2 * pad - kw + 1
    return out.reshape(B, C_out, out_h, out_w)


def group_norm(x: np.ndarray, gamma: np.ndarray, beta: np.ndarray, groups: int,
               eps: float = 1e-5) -> np.ndarray:
    B, C, H, W = x.shape
    G = groups
    assert C % G == 0
    xg = x.reshape(B, G, C // G, H, W)
    mean = xg.mean(axis=(2, 3, 4), keepdims=True)
    var = xg.var(axis=(2, 3, 4), keepdims=True)
    xg = (xg - mean) / np.sqrt(var + eps)
    x = xg.reshape(B, C, H, W)
    return x * gamma.reshape(1, C, 1, 1) + beta.reshape(1, C, 1, 1)


class ResBlock:
    """Conv -> GN -> adaGN-style FiLM from time+text -> ReLU -> Conv -> GN -> residual."""

    def __init__(self, in_ch: int, out_ch: int, time_dim: int, text_dim: int,
                 rng: np.random.Generator):
        self.in_ch = in_ch
        self.out_ch = out_ch
        k = 3
        self.k = k
        scale = (1.0 / max(1.0, in_ch * k * k)) ** 0.5
        self.w1 = (rng.standard_normal((out_ch, in_ch, k, k)) * scale).astype(np.float32)
        self.b1 = np.zeros((out_ch,), dtype=np.float32)
        self.w2 = (rng.standard_normal((out_ch, out_ch, k, k)) * scale).astype(np.float32)
        self.b2 = np.zeros((out_ch,), dtype=np.float32)
        self.gn1_g = np.ones((out_ch,), dtype=np.float32)
        self.gn1_b = np.zeros((out_ch,), dtype=np.float32)
        self.gn2_g = np.ones((out_ch,), dtype=np.float32)
        self.gn2_b = np.zeros((out_ch,), dtype=np.float32)
        # FiLM modulation: scale & shift from time+text
        cond_dim = time_dim + text_dim
        self.film1 = (rng.standard_normal((out_ch * 2, cond_dim)) * (1.0 / cond_dim ** 0.5)).astype(np.float32)
        self.film2 = (rng.standard_normal((out_ch * 2, cond_dim)) * (1.0 / cond_dim ** 0.5)).astype(np.float32)
        if in_ch != out_ch:
            self.skip = (rng.standard_normal((out_ch, in_ch, 1, 1)) * scale).astype(np.float32)
        else:
            self.skip = None

    def __call__(self, x: np.ndarray, t_emb: np.ndarray, txt_emb: np.ndarray) -> np.ndarray:
        cond = np.concatenate([t_emb, txt_emb], axis=1)  # (B, cond_dim)
        film1 = cond @ self.film1.T  # (B, 2*out_ch)
        scale1, shift1 = film1[:, :self.out_ch], film1[:, self.out_ch:]
        film2 = cond @ self.film2.T
        scale2, shift2 = film2[:, :self.out_ch], film2[:, self.out_ch:]
        h = conv2d_forward(x, self.w1, self.b1, pad=1)
        h = group_norm(h, self.gn1_g, self.gn1_b, groups=1)
        h = h * (1.0 + scale1[:, :, None, None]) + shift1[:, :, None, None]
        h = np.maximum(0.0, h)
        h = conv2d_forward(h, self.w2, self.b2, pad=1)
        h = group_norm(h, self.gn2_g, self.gn2_b, groups=1)
        h = h * (1.0 + scale2[:, :, None, None]) + shift2[:, :, None, None]
        if self.skip is not None:
            x = conv2d_forward(x, self.skip, np.zeros(self.out_ch, dtype=np.float32))
        return np.maximum(0.0, h + x)


class Downsample:
    def __init__(self, ch: int, rng: np.random.Generator):
        # 2x2 average pool (no params)
        self.ch = ch

    def __call__(self, x: np.ndarray) -> np.ndarray:
        B, C, H, W = x.shape
        return x.reshape(B, C, H // 2, 2, W // 2, 2).mean(axis=(3, 5))


class Upsample:
    def __init__(self, ch: int, rng: np.random.Generator):
        self.ch = ch

    def __call__(self, x: np.ndarray) -> np.ndarray:
        B, C, H, W = x.shape
        out = np.zeros((B, C, H * 2, W * 2), dtype=x.dtype)
        out[:, :, ::2, ::2] = x
        out[:, :, 1::2, ::2] = x
        out[:, :, ::2, 1::2] = x
        out[:, :, 1::2, 1::2] = x
        return out * 0.25


class NumpyUNet:
    """Tiny single-level UNet denoiser. No spatial downsampling.

    Architecture: stem -> [resblock]*N -> [resblock]*M (mid) -> [resblock]*N (decoder with skip
    concatenation) -> group norm -> relu -> output conv. Spatial size is preserved throughout.
    All decoder resblocks take 2x the bottleneck channels because of the skip concat.

    This is the simplest UNet shape that still has the encoder-decoder
    skip-connection structure characteristic of UNet diffusion models.
    """

    def __init__(self, cfg: NumpyUNetConfig, seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.time_mlp_w1 = (self.rng.standard_normal((cfg.time_dim * 2, cfg.time_dim))
                            * (1.0 / cfg.time_dim ** 0.5)).astype(np.float32)
        self.time_mlp_w2 = (self.rng.standard_normal((cfg.time_dim, cfg.time_dim * 2))
                            * (1.0 / (cfg.time_dim * 2) ** 0.5)).astype(np.float32)
        ch = cfg.base_channels
        # Stem
        k = 3
        self.stem_w = (self.rng.standard_normal((ch, cfg.in_channels, k, k))
                       * (1.0 / (cfg.in_channels * k * k) ** 0.5)).astype(np.float32)
        self.stem_b = np.zeros((ch,), dtype=np.float32)
        # Encoder (single level, no downsampling)
        in_ch = ch
        out_ch = ch
        self.enc_blocks: List[ResBlock] = []
        for _ in range(cfg.num_res_blocks):
            self.enc_blocks.append(ResBlock(in_ch, out_ch, cfg.time_dim, cfg.text_dim, self.rng))
            in_ch = out_ch
        # Bottleneck
        self.mid1 = ResBlock(in_ch, in_ch, cfg.time_dim, cfg.text_dim, self.rng)
        self.mid2 = ResBlock(in_ch, in_ch, cfg.time_dim, cfg.text_dim, self.rng)
        # Decoder: each block takes concat(skip, h) -> 2*in_ch, outputs in_ch
        self.dec_blocks: List[ResBlock] = []
        for j in range(cfg.num_res_blocks):
            self.dec_blocks.append(ResBlock(in_ch * 2, out_ch, cfg.time_dim, cfg.text_dim, self.rng))
            in_ch = out_ch
        # Output projection
        self.out_w = (self.rng.standard_normal((cfg.in_channels, in_ch, 3, 3))
                      * (1.0 / (in_ch * 9) ** 0.5)).astype(np.float32)
        self.out_b = np.zeros((cfg.in_channels,), dtype=np.float32)
        self.out_gn_g = np.ones((in_ch,), dtype=np.float32)
        self.out_gn_b = np.zeros((in_ch,), dtype=np.float32)
        self._cache_param_specs()

    def _cache_param_specs(self) -> None:
        specs: List[Tuple[str, np.ndarray]] = []
        for name in (
            "stem_w", "stem_b",
            "time_mlp_w1", "time_mlp_w2",
            "out_w", "out_b", "out_gn_g", "out_gn_b",
        ):
            specs.append((name, getattr(self, name)))
        for i, rb in enumerate(self.enc_blocks):
            for name in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "film1", "film2"):
                specs.append((f"enc{i}_{name}", getattr(rb, name)))
            if rb.skip is not None:
                specs.append((f"enc{i}_skip", rb.skip))
        for i, rb in enumerate([self.mid1, self.mid2]):
            for name in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "film1", "film2"):
                specs.append((f"mid{i}_{name}", getattr(rb, name)))
            if rb.skip is not None:
                specs.append((f"mid{i}_skip", rb.skip))
        for i, rb in enumerate(self.dec_blocks):
            for name in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "film1", "film2"):
                specs.append((f"dec{i}_{name}", getattr(rb, name)))
            if rb.skip is not None:
                specs.append((f"dec{i}_skip", rb.skip))
        self._param_specs = specs

    def parameters(self) -> Dict[str, np.ndarray]:
        return {name: arr for name, arr in self._param_specs}

    def state_dict(self) -> Dict[str, np.ndarray]:
        return {name: np.array(arr, copy=True) for name, arr in self._param_specs}

    def load_state_dict(self, sd: Dict[str, np.ndarray], strict: bool = True) -> None:
        for name, arr in self._param_specs:
            if name not in sd:
                if strict:
                    raise KeyError(f"missing param {name}")
                continue
            arr[...] = sd[name]

    def time_embedding(self, t: np.ndarray) -> np.ndarray:
        emb = _sinusoidal_embedding(t, self.cfg.time_dim)
        h = np.maximum(0.0, emb @ self.time_mlp_w1.T)
        return h @ self.time_mlp_w2.T

    def forward(self, x: np.ndarray, t: np.ndarray, prompt: str = "") -> np.ndarray:
        cfg = self.cfg
        if t.ndim == 0:
            t = np.array([int(t)], dtype=np.int64)
        t = t.astype(np.int64)
        t_emb = self.time_embedding(t)
        txt = _prompt_embedding(prompt, cfg.text_dim)
        txt_emb = np.broadcast_to(txt[None, :], (t.shape[0], cfg.text_dim)).copy()
        h = conv2d_forward(x, self.stem_w, self.stem_b, pad=1)
        skips = []
        for rb in self.enc_blocks:
            h = rb(h, t_emb, txt_emb)
            skips.append(h)
        h = self.mid1(h, t_emb, txt_emb)
        h = self.mid2(h, t_emb, txt_emb)
        for j, rb in enumerate(self.dec_blocks):
            skip = skips.pop()
            h = np.concatenate([h, skip], axis=1)
            h = rb(h, t_emb, txt_emb)
        h = group_norm(h, self.out_gn_g, self.out_gn_b, groups=1)
        h = np.maximum(0.0, h)
        out = conv2d_forward(h, self.out_w, self.out_b, pad=1)
        return out


def count_params(model: NumpyUNet) -> int:
    return int(sum(arr.size for _, arr in model._param_specs))