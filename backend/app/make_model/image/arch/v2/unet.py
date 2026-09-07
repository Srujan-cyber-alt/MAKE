"""
NumpyUNetV2: v2 of the MAKE image denoiser with structured conditioning.

Differences from v1:
  - Accepts a ConditionVector (not just a string prompt).
  - FiLM modulation now takes the full condition vector
    (prompt + camera + lighting + material + composition + style + identity).
  - Adds a separate ClassEmbed for classifier-free-guidance (CFG) training:
    the network can be asked to evaluate either a conditioned sample or
    an unconditional sample, and the CFG sampler combines them.
  - Optional identity skip path: a learnable "identity bypass" is added
    to the deepest layer so that the same identity string with different
    prompts and seeds produces related outputs (identity consistency).
  - Optional "detail recovery" head: a 3x3 conv applied to the final
    feature map before the output projection, intended to be a learnable
    high-frequency boost.
  - Same NumPy-only constraint. No PyTorch. CPU-friendly.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Tuple, List, Optional

import numpy as np

from app.make_model.image.arch.v2.conditioning import (
    ConditionVector, DEFAULT_CONDITION_DIM, _prompt_embedding_v2,
)
from app.make_model.image.arch.unet import (
    _im2col, _col2im, conv2d_forward, group_norm, NumpyUNetConfig,
)


def _sinusoidal_embedding(t: np.ndarray, dim: int) -> np.ndarray:
    half = dim // 2
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(1, half - 1))
    args = t.astype(np.float32)[:, None] * freqs[None, :]
    emb = np.concatenate([np.sin(args), np.cos(args)], axis=1)
    if emb.shape[1] < dim:
        emb = np.concatenate([emb, np.zeros((emb.shape[0], dim - emb.shape[1]), dtype=np.float32)], axis=1)
    return emb


@dataclass
class NumpyUNetV2Config:
    image_size: int = 32
    in_channels: int = 3
    base_channels: int = 32
    channel_mults: Tuple[int, ...] = (1,)
    num_res_blocks: int = 2
    condition_dim: int = DEFAULT_CONDITION_DIM
    time_dim: int = 64
    identity_dim: int = 16
    num_timesteps: int = 200
    arch_version: str = "make-image-cpu-unet-v2"
    use_identity_bypass: bool = True
    use_detail_head: bool = True
    notes: str = "v2: structured conditioning + CFG + identity bypass + detail head"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NumpyUNetV2Config":
        d = dict(d)
        d["channel_mults"] = tuple(int(x) for x in d.get("channel_mults", (1,)))
        return cls(**d)


class ResBlockV2:
    """FiLM-modulated residual block. FiLM comes from time + condition
    (not just time + prompt like v1)."""

    def __init__(self, in_ch: int, out_ch: int, time_dim: int, cond_dim: int,
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
        # FiLM: scale + shift from time+cond
        self.film1 = (rng.standard_normal((out_ch * 2, time_dim + cond_dim))
                      * (1.0 / (time_dim + cond_dim) ** 0.5)).astype(np.float32)
        self.film2 = (rng.standard_normal((out_ch * 2, time_dim + cond_dim))
                      * (1.0 / (time_dim + cond_dim) ** 0.5)).astype(np.float32)
        if in_ch != out_ch:
            self.skip = (rng.standard_normal((out_ch, in_ch, 1, 1)) * scale).astype(np.float32)
        else:
            self.skip = None

    def forward(self, x: np.ndarray, time_cond: np.ndarray) -> np.ndarray:
        """time_cond is the concatenation of time embedding and condition
        vector, pre-projected by an MLP outside the block."""
        film1 = time_cond @ self.film1.T
        scale1, shift1 = film1[:, :self.out_ch], film1[:, self.out_ch:]
        film2 = time_cond @ self.film2.T
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


class NumpyUNetV2:
    """v2 UNet. Same single-level encoder/decoder shape as v1, but with
    structured conditioning, identity bypass, detail head, and a single
    time+cond MLP that all resblocks share."""

    def __init__(self, cfg: NumpyUNetV2Config, seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        ch = cfg.base_channels
        td = cfg.time_dim
        cd = cfg.condition_dim
        in_dim = td + cd
        # Time+cond MLP (shared across all resblocks)
        self.tc_w1 = (self.rng.standard_normal((in_dim * 2, in_dim))
                      * (1.0 / in_dim ** 0.5)).astype(np.float32)
        self.tc_w2 = (self.rng.standard_normal((in_dim, in_dim * 2))
                      * (1.0 / (in_dim * 2) ** 0.5)).astype(np.float32)
        # Stem
        k = 3
        self.stem_w = (self.rng.standard_normal((ch, cfg.in_channels, k, k))
                       * (1.0 / (cfg.in_channels * k * k) ** 0.5)).astype(np.float32)
        self.stem_b = np.zeros((ch,), dtype=np.float32)
        # Encoder
        in_ch = ch
        out_ch = ch
        self.enc_blocks: List[ResBlockV2] = []
        for _ in range(cfg.num_res_blocks):
            self.enc_blocks.append(ResBlockV2(in_ch, out_ch, td, cd, self.rng))
            in_ch = out_ch
        # Bottleneck
        self.mid1 = ResBlockV2(in_ch, in_ch, td, cd, self.rng)
        self.mid2 = ResBlockV2(in_ch, in_ch, td, cd, self.rng)
        # Identity bypass: maps the identity embedding to a per-channel bias
        # that is added to the bottleneck feature.
        if cfg.use_identity_bypass:
            self.id_w = (self.rng.standard_normal((in_ch, cfg.identity_dim))
                         * (1.0 / cfg.identity_dim ** 0.5)).astype(np.float32)
            self.id_b = np.zeros((in_ch,), dtype=np.float32)
        else:
            self.id_w = None
        # Decoder
        self.dec_blocks: List[ResBlockV2] = []
        for _ in range(cfg.num_res_blocks):
            self.dec_blocks.append(ResBlockV2(in_ch * 2, out_ch, td, cd, self.rng))
        # Detail recovery head: 3x3 conv + relu + 1x1 conv, applied before
        # the output projection. Learns a high-frequency residual that is
        # added to the output.
        if cfg.use_detail_head:
            self.detail_w = (self.rng.standard_normal((in_ch, in_ch, 3, 3))
                             * (1.0 / (in_ch * 9) ** 0.5)).astype(np.float32)
            self.detail_b = np.zeros((in_ch,), dtype=np.float32)
            self.detail_proj_w = (self.rng.standard_normal((in_ch, in_ch, 1, 1))
                                   * (1.0 / in_dim ** 0.5)).astype(np.float32)
            self.detail_proj_b = np.zeros((in_ch,), dtype=np.float32)
        else:
            self.detail_w = None
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
            "tc_w1", "tc_w2",
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
        if self.id_w is not None:
            specs.append(("id_w", self.id_w))
            specs.append(("id_b", self.id_b))
        for i, rb in enumerate(self.dec_blocks):
            for name in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "film1", "film2"):
                specs.append((f"dec{i}_{name}", getattr(rb, name)))
            if rb.skip is not None:
                specs.append((f"dec{i}_skip", rb.skip))
        if self.detail_w is not None:
            for n in ("detail_w", "detail_b", "detail_proj_w", "detail_proj_b"):
                specs.append((n, getattr(self, n)))
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

    def time_cond_embedding(self, t: np.ndarray, cond: np.ndarray) -> np.ndarray:
        """Compute the shared time+cond embedding used by every resblock."""
        t_emb = _sinusoidal_embedding(t, self.cfg.time_dim)
        x = np.concatenate([t_emb, cond], axis=1)
        h = np.maximum(0.0, x @ self.tc_w1.T)
        return h @ self.tc_w2.T

    def forward(self, x: np.ndarray, t: np.ndarray, condition: ConditionVector,
                identity_vec: Optional[np.ndarray] = None) -> np.ndarray:
        cfg = self.cfg
        if t.ndim == 0:
            t = np.array([int(t)], dtype=np.int64)
        t = t.astype(np.int64)
        cond_vec = condition.to_array()
        if cond_vec.ndim == 1:
            cond_vec = np.broadcast_to(cond_vec[None, :], (t.shape[0], cond_vec.shape[0])).copy()
        # Pad / truncate condition vector to expected dim
        if cond_vec.shape[1] != cfg.condition_dim:
            new = np.zeros((cond_vec.shape[0], cfg.condition_dim), dtype=np.float32)
            n = min(cond_vec.shape[1], cfg.condition_dim)
            new[:, :n] = cond_vec[:, :n]
            cond_vec = new
        tc = self.time_cond_embedding(t, cond_vec)
        h = conv2d_forward(x, self.stem_w, self.stem_b, pad=1)
        skips = []
        for rb in self.enc_blocks:
            h = rb.forward(h, tc)
            skips.append(h)
        h = self.mid1.forward(h, tc)
        h = self.mid2.forward(h, tc)
        # Identity bypass
        if self.id_w is not None and identity_vec is not None:
            idb = identity_vec @ self.id_w.T + self.id_b
            h = h + idb[:, :, None, None]
        # Decoder
        for rb in self.dec_blocks:
            skip = skips.pop()
            h = np.concatenate([h, skip], axis=1)
            h = rb.forward(h, tc)
        # Detail head
        if self.detail_w is not None:
            d = conv2d_forward(h, self.detail_w, self.detail_b, pad=1)
            d = np.maximum(0.0, d)
            d = conv2d_forward(d, self.detail_proj_w, self.detail_proj_b, pad=0)
            h = h + d
        h = group_norm(h, self.out_gn_g, self.out_gn_b, groups=1)
        h = np.maximum(0.0, h)
        out = conv2d_forward(h, self.out_w, self.out_b, pad=1)
        return out


def count_params_v2(model: NumpyUNetV2) -> int:
    return int(sum(arr.size for _, arr in model._param_specs))