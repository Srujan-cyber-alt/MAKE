"""
v3 multi-scale UNet for the MAKE image subsystem.

Goals vs v2:
  - Multi-scale: 1/2 -> 1/4 -> 1/8 spatial downsample with skip
    connections. At 32x32 this means 32, 16, 8 resolutions.
  - AdaGN: Adaptive Group Normalization with per-timestep and per-condition
    scale/shift (true StyleGAN-style AdaGN, not just FiLM on a hidden
    state).
  - Cross-attention at the deepest level only (1/8 of 32x32 = 4x4, 8
    tokens). Linear-cost attention: O(seq^2 * head_dim).
  - Latent self-attention block (Transformer-style) at the deepest
    level so the conditioning can influence global structure.
  - All ops are still NumPy. No PyTorch. CPU-friendly.

The forward is split into a list of named steps so the trainer can
reuse the v3 forward with or without autograd (autograd is only needed
during training).
"""

from __future__ import annotations

import math
import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional, Sequence

import numpy as np

from app.make_model.image.arch.v2.conditioning import (
    ConditionVector, DEFAULT_CONDITION_DIM, _identity_embedding,
)
from app.make_model.image.arch.unet import (
    _im2col, _col2im, conv2d_forward, group_norm, NumpyUNetConfig,
)


# ---------------------------------------------------------------------------
# Cross-attention (NumPy)
# ---------------------------------------------------------------------------


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_max = np.max(x, axis=axis, keepdims=True)
    e = np.exp(x - x_max)
    return e / np.sum(e, axis=axis, keepdims=True)


def multi_head_cross_attention(
    q_in: np.ndarray,      # (B, Tq, C)
    kv_in: np.ndarray,     # (B, Tk, Ckv) — for self-attn same as q
    w_q: np.ndarray, w_k: np.ndarray, w_v: np.ndarray, w_o: np.ndarray,
    b_q: np.ndarray, b_k: np.ndarray, b_v: np.ndarray, b_o: np.ndarray,
    num_heads: int = 4,
) -> np.ndarray:
    B, Tq, C = q_in.shape
    Tk = kv_in.shape[1]
    head_dim = max(1, C // num_heads)
    inner_dim = num_heads * head_dim
    # Reshape into (B, num_heads, T, head_dim) without projection yet
    qr = q_in.reshape(B, Tq, num_heads, head_dim).transpose(0, 2, 1, 3)  # B,H,Tq,D
    kr = kv_in.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
    vr = kv_in.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
    # Per-head projections
    # w_q is (num_heads, head_dim, head_dim); apply to last dim of qr
    # If w_q is (C, C), it's actually a joint projection. We support both:
    if w_q.shape == (C, C):
        # Joint projection
        qp = q_in @ w_q.T + b_q.reshape(1, 1, -1)
        kp = kv_in @ w_k.T + b_k.reshape(1, 1, -1)
        vp = kv_in @ w_v.T + b_v.reshape(1, 1, -1)
        q = qp.reshape(B, Tq, num_heads, head_dim).transpose(0, 2, 1, 3)
        k = kp.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
        v = vp.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
    else:
        # Per-head weights: w_q is (num_heads, head_dim, head_dim)
        q = np.einsum("bhqd,hde->bhqe", qr, w_q) + b_q.reshape(1, num_heads, 1, head_dim)
        k = np.einsum("bhkd,hde->bhke", kr, w_k) + b_k.reshape(1, num_heads, 1, head_dim)
        v = np.einsum("bhkd,hde->bhke", vr, w_v) + b_v.reshape(1, num_heads, 1, head_dim)
    # Attention scores
    scale = 1.0 / math.sqrt(head_dim)
    scores = np.einsum("bhqd,bhkd->bhqk", q, k) * scale
    attn = _softmax(scores, axis=-1)
    out = np.einsum("bhqk,bhkd->bhqd", attn, v)
    out = out.transpose(0, 2, 1, 3).reshape(B, Tq, C)
    out = out @ w_o.T + b_o.reshape(1, 1, -1)
    return out


# ---------------------------------------------------------------------------
# AdaGN
# ---------------------------------------------------------------------------


def adagn(x: np.ndarray, scale: np.ndarray, shift: np.ndarray,
          groups: int = 1, eps: float = 1e-5) -> np.ndarray:
    """Adaptive Group Norm: GN with learned per-timestep / per-condition
    scale and shift applied to the normalized output.

    x:     (B, C, H, W)
    scale: (B, C)
    shift: (B, C)
    """
    B, C, H, W = x.shape
    if groups <= 0:
        groups = 1
    Cg = C // groups
    xr = x.reshape(B, groups, Cg, H, W)
    mean = xr.mean(axis=(2, 3, 4), keepdims=True)
    var = xr.var(axis=(2, 3, 4), keepdims=True)
    xn = (xr - mean) / np.sqrt(var + eps)
    xn = xn.reshape(B, C, H, W)
    out = xn * (1.0 + scale[:, :, None, None]) + shift[:, :, None, None]
    return out


# ---------------------------------------------------------------------------
# v3 ResBlock with AdaGN
# ---------------------------------------------------------------------------


class AdaGNResBlock:
    """3x3 -> AdaGN -> 3x3 -> AdaGN -> residual add.

    FiLM-style modulation: time+cond -> MLP -> (gamma1, beta1, gamma2, beta2)
    in addition to per-channel group normalization parameters.
    """

    def __init__(self, in_ch: int, out_ch: int, tcc_dim: int,
                 rng: np.random.Generator, groups: int = 4):
        self.in_ch, self.out_ch = in_ch, out_ch
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
        # AdaGN modulation: 4 * out_ch outputs from tcc_dim
        self.mod = (rng.standard_normal((out_ch * 4, tcc_dim)) * (1.0 / tcc_dim ** 0.5)).astype(np.float32)
        self.gn1_groups = min(groups, max(1, out_ch))
        self.gn2_groups = min(groups, max(1, out_ch))
        if in_ch != out_ch:
            self.skip = (rng.standard_normal((out_ch, in_ch, 1, 1)) * scale).astype(np.float32)
        else:
            self.skip = None

    def forward(self, x: np.ndarray, tcc: np.ndarray) -> np.ndarray:
        mod = tcc @ self.mod.T
        out_ch = self.out_ch
        gamma1 = mod[:, :out_ch]
        beta1 = mod[:, out_ch:2*out_ch]
        gamma2 = mod[:, 2*out_ch:3*out_ch]
        beta2 = mod[:, 3*out_ch:4*out_ch]
        h = conv2d_forward(x, self.w1, self.b1, pad=1)
        h = group_norm(h, self.gn1_g, self.gn1_b, groups=1)
        h = adagn(h, gamma1, beta1, groups=self.gn1_groups)
        h = np.maximum(0.0, h)
        h = conv2d_forward(h, self.w2, self.b2, pad=1)
        h = group_norm(h, self.gn2_g, self.gn2_b, groups=1)
        h = adagn(h, gamma2, beta2, groups=self.gn2_groups)
        if self.skip is not None:
            x = conv2d_forward(x, self.skip, np.zeros(self.out_ch, dtype=np.float32))
        h = h + x
        h = np.maximum(0.0, h)
        return h


class LatentAttentionBlock:
    """Spatial self-attention at the deepest latent resolution.

    Input:  (B, C, H, W). We flatten to (B, H*W, C) tokens, run a
    Transformer block, reshape back.
    """

    def __init__(self, channels: int, num_heads: int, tcc_dim: int,
                 rng: np.random.Generator, mlp_ratio: float = 2.0):
        self.channels = channels
        self.num_heads = num_heads
        head_dim = max(1, channels // num_heads)
        self.head_dim = head_dim
        scale = (1.0 / channels) ** 0.5
        self.ln_g = np.ones((channels,), dtype=np.float32)
        self.ln_b = np.zeros((channels,), dtype=np.float32)
        # QKV from channels
        self.w_q = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_q = np.zeros((channels,), dtype=np.float32)
        self.w_k = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_k = np.zeros((channels,), dtype=np.float32)
        self.w_v = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_v = np.zeros((channels,), dtype=np.float32)
        self.w_o = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_o = np.zeros((channels,), dtype=np.float32)
        # AdaGN modulation
        self.mod_ln = (rng.standard_normal((channels * 2, tcc_dim)) * (1.0 / tcc_dim ** 0.5)).astype(np.float32)
        # MLP
        mlp_hidden = max(channels, int(channels * mlp_ratio))
        self.w_mlp1 = (rng.standard_normal((mlp_hidden, channels)) * scale).astype(np.float32)
        self.b_mlp1 = np.zeros((mlp_hidden,), dtype=np.float32)
        self.w_mlp2 = (rng.standard_normal((channels, mlp_hidden)) * scale).astype(np.float32)
        self.b_mlp2 = np.zeros((channels,), dtype=np.float32)
        self.mod_mlp = (rng.standard_normal((channels * 2, tcc_dim)) * (1.0 / tcc_dim ** 0.5)).astype(np.float32)
        # Conditioning cross-attn (optional): condition vector attends to
        # the spatial tokens. For CPU efficiency we collapse cond into a
        # single token and let it bias the MLP via AdaGN (no extra K/V).

    def forward(self, x: np.ndarray, tcc: np.ndarray) -> np.ndarray:
        B, C, H, W = x.shape
        # Save residual
        residual = x
        # AdaGN on input
        mod1 = tcc @ self.mod_ln.T
        gamma = mod1[:, :C]; beta = mod1[:, C:]
        x = group_norm(x, self.ln_g, self.ln_b, groups=1)
        x = adagn(x, gamma, beta)
        # Self-attention
        xn = x.reshape(B, C, H * W).transpose(0, 2, 1)  # (B, T, C)
        out = multi_head_cross_attention(
            xn, xn, self.w_q, self.w_k, self.w_v, self.w_o,
            self.b_q, self.b_k, self.b_v, self.b_o,
            num_heads=self.num_heads,
        )
        out = out.transpose(0, 2, 1).reshape(B, C, H, W)
        x = residual + out
        # MLP block
        residual = x
        mod2 = tcc @ self.mod_mlp.T
        gamma2 = mod2[:, :C]; beta2 = mod2[:, C:]
        xn = group_norm(x, self.ln_g, self.ln_b, groups=1)
        xn = adagn(xn, gamma2, beta2)
        xn = xn.reshape(B, C, H * W).transpose(0, 2, 1)  # (B, T, C)
        h = np.maximum(0.0, xn @ self.w_mlp1.T + self.b_mlp1)
        h = h @ self.w_mlp2.T + self.b_mlp2
        h = h.transpose(0, 2, 1).reshape(B, C, H, W)
        return residual + h


# ---------------------------------------------------------------------------
# v3 Config + UNet
# ---------------------------------------------------------------------------


@dataclass
class NumpyUNetV3Config:
    image_size: int = 32
    in_channels: int = 3
    base_channels: int = 32
    channel_mults: Tuple[int, ...] = (1, 2, 4)
    num_res_blocks: int = 2
    condition_dim: int = DEFAULT_CONDITION_DIM
    time_dim: int = 64
    identity_dim: int = 16
    num_timesteps: int = 200
    arch_version: str = "make-image-cpu-unet-v3"
    attention_resolution: int = 8
    num_attention_heads: int = 4
    use_identity_bypass: bool = True
    use_detail_head: bool = True
    notes: str = "v3: multi-scale + AdaGN + spatial self-attention"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NumpyUNetV3Config":
        d = dict(d)
        d["channel_mults"] = tuple(int(x) for x in d.get("channel_mults", (1, 2, 4)))
        return cls(**d)


class NumpyUNetV3:
    def __init__(self, cfg: NumpyUNetV3Config, seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        td, cd = cfg.time_dim, cfg.condition_dim
        in_dim = td + cd
        # Time+cond MLP
        self.tc_w1 = (self.rng.standard_normal((in_dim * 2, in_dim)) * (1.0 / in_dim ** 0.5)).astype(np.float32)
        self.tc_w2 = (self.rng.standard_normal((in_dim, in_dim * 2)) * (1.0 / (in_dim * 2) ** 0.5)).astype(np.float32)
        # Stem
        k = 3
        ch = cfg.base_channels
        self.stem_w = (self.rng.standard_normal((ch, cfg.in_channels, k, k)) * (1.0 / (cfg.in_channels * k * k) ** 0.5)).astype(np.float32)
        self.stem_b = np.zeros((ch,), dtype=np.float32)
        # Encoder levels
        self.enc_levels: List[Dict[str, Any]] = []
        cur_ch = ch
        resolution = cfg.image_size
        for level, mult in enumerate(cfg.channel_mults):
            out_ch = ch * mult
            blocks = [AdaGNResBlock(cur_ch if i == 0 else out_ch, out_ch, in_dim, self.rng, groups=4)
                      for i in range(cfg.num_res_blocks)]
            self.enc_levels.append({
                "blocks": blocks,
                "out_ch": out_ch,
                "in_ch_first": cur_ch,
                "downsample": level < len(cfg.channel_mults) - 1,
            })
            cur_ch = out_ch
            if level < len(cfg.channel_mults) - 1:
                resolution //= 2
        # Bottleneck AdaGNResBlocks
        self.mid1 = AdaGNResBlock(cur_ch, cur_ch, in_dim, self.rng, groups=4)
        self.mid2 = AdaGNResBlock(cur_ch, cur_ch, in_dim, self.rng, groups=4)
        # Attention at deepest latent
        if resolution <= cfg.attention_resolution and cfg.attention_resolution > 0:
            self.attn = LatentAttentionBlock(cur_ch, cfg.num_attention_heads, in_dim, self.rng, mlp_ratio=2.0)
        else:
            self.attn = None
        # Identity bypass at bottleneck
        if cfg.use_identity_bypass:
            self.id_w = (self.rng.standard_normal((cur_ch, cfg.identity_dim)) * (1.0 / cfg.identity_dim ** 0.5)).astype(np.float32)
            self.id_b = np.zeros((cur_ch,), dtype=np.float32)
        else:
            self.id_w = None
        # Decoder levels (mirror). For each level the in_ch_first is
        # the concat of: cur_ch (output of previous deeper level after
        # upsample) + skip.out_ch.
        self.dec_levels: List[Dict[str, Any]] = []
        for level in reversed(range(len(cfg.channel_mults))):
            skip_ch = cfg.base_channels * cfg.channel_mults[level]
            in_ch_dec = cur_ch + skip_ch
            out_ch = skip_ch
            blocks = [AdaGNResBlock(in_ch_dec if i == 0 else out_ch, out_ch, in_dim, self.rng, groups=4)
                      for i in range(cfg.num_res_blocks)]
            self.dec_levels.append({
                "blocks": blocks,
                "out_ch": out_ch,
                "in_ch_first": in_ch_dec,
                "level": level,
            })
            cur_ch = out_ch
        # Detail head
        if cfg.use_detail_head:
            self.detail_w = (self.rng.standard_normal((cur_ch, cur_ch, 3, 3)) * (1.0 / (cur_ch * 9) ** 0.5)).astype(np.float32)
            self.detail_b = np.zeros((cur_ch,), dtype=np.float32)
            self.detail_proj_w = (self.rng.standard_normal((cur_ch, cur_ch, 1, 1)) * (1.0 / cur_ch ** 0.5)).astype(np.float32)
            self.detail_proj_b = np.zeros((cur_ch,), dtype=np.float32)
        else:
            self.detail_w = None
        # Output
        self.out_w = (self.rng.standard_normal((cfg.in_channels, cur_ch, 3, 3)) * (1.0 / (cur_ch * 9) ** 0.5)).astype(np.float32)
        self.out_b = np.zeros((cfg.in_channels,), dtype=np.float32)
        self.out_gn_g = np.ones((cur_ch,), dtype=np.float32)
        self.out_gn_b = np.zeros((cur_ch,), dtype=np.float32)
        self._cache_param_specs()

    def _cache_param_specs(self) -> None:
        specs: List[Tuple[str, np.ndarray]] = []
        for n in ("stem_w", "stem_b", "tc_w1", "tc_w2",
                 "out_w", "out_b", "out_gn_g", "out_gn_b"):
            specs.append((n, getattr(self, n)))
        for li, lvl in enumerate(self.enc_levels):
            for bi, rb in enumerate(lvl["blocks"]):
                for n in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "mod"):
                    specs.append((f"enc{li}_b{bi}_{n}", getattr(rb, n)))
                if rb.skip is not None:
                    specs.append((f"enc{li}_b{bi}_skip", rb.skip))
        for mi in (0, 1):
            rb = getattr(self, f"mid{mi+1}")
            for n in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "mod"):
                specs.append((f"mid{mi}_{n}", getattr(rb, n)))
            if rb.skip is not None:
                specs.append((f"mid{mi}_skip", rb.skip))
        if self.attn is not None:
            for n in ("ln_g", "ln_b",
                     "w_q", "b_q", "w_k", "b_k", "w_v", "b_v", "w_o", "b_o",
                     "mod_ln", "w_mlp1", "b_mlp1", "w_mlp2", "b_mlp2", "mod_mlp"):
                specs.append((f"attn_{n}", getattr(self.attn, n)))
        if self.id_w is not None:
            specs.append(("id_w", self.id_w))
            specs.append(("id_b", self.id_b))
        for li, lvl in enumerate(self.dec_levels):
            for bi, rb in enumerate(lvl["blocks"]):
                for n in ("w1", "b1", "w2", "b2", "gn1_g", "gn1_b", "gn2_g", "gn2_b", "mod"):
                    specs.append((f"dec{li}_b{bi}_{n}", getattr(rb, n)))
                if rb.skip is not None:
                    specs.append((f"dec{li}_b{bi}_skip", rb.skip))
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
            if name in sd:
                arr[...] = sd[name]
            elif strict:
                raise KeyError(f"missing param {name}")

    # Forward
    def _tcc(self, t: np.ndarray, cond_vec: np.ndarray) -> np.ndarray:
        half = self.cfg.time_dim // 2
        freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(1, half - 1))
        args = t.astype(np.float32)[:, None] * freqs[None, :]
        emb = np.concatenate([np.sin(args), np.cos(args)], axis=1)
        if emb.shape[1] < self.cfg.time_dim:
            emb = np.concatenate([emb, np.zeros((emb.shape[0], self.cfg.time_dim - emb.shape[1]), dtype=np.float32)], axis=1)
        x = np.concatenate([emb, cond_vec], axis=1)
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
        if cond_vec.shape[1] != cfg.condition_dim:
            new = np.zeros((cond_vec.shape[0], cfg.condition_dim), dtype=np.float32)
            n_ = min(cond_vec.shape[1], cfg.condition_dim)
            new[:, :n_] = cond_vec[:, :n_]
            cond_vec = new
        tcc = self._tcc(t, cond_vec)
        h = conv2d_forward(x, self.stem_w, self.stem_b, pad=1)
        skips = []
        for lvl in self.enc_levels:
            for rb in lvl["blocks"]:
                h = rb.forward(h, tcc)
            skips.append((h, lvl["out_ch"]))
            if lvl["downsample"]:
                h = _avg_pool_2x2(h)
        # Bottleneck
        h = self.mid1.forward(h, tcc)
        h = self.mid2.forward(h, tcc)
        if self.attn is not None:
            h = self.attn.forward(h, tcc)
        if self.id_w is not None and identity_vec is not None:
            idb = identity_vec @ self.id_w.T + self.id_b
            b, c = idb.shape
            bcast = idb.reshape(b, c, 1, 1) + np.zeros((1, 1, h.shape[2], h.shape[3]), dtype=np.float32)
            h = h + bcast
        # Decoder
        for li, lvl in enumerate(self.dec_levels):
            skip_h, skip_ch = skips.pop()
            # Up-concat
            if h.shape[2] != skip_h.shape[2] or h.shape[3] != skip_h.shape[3]:
                h = _upsample_2x2(h)
            h = np.concatenate([h, skip_h], axis=1)
            for rb in lvl["blocks"]:
                h = rb.forward(h, tcc)
        # Detail head
        if self.detail_w is not None:
            d = conv2d_forward(h, self.detail_w, self.detail_b, pad=1)
            d = np.maximum(0.0, d)
            d = conv2d_forward(d, self.detail_proj_w, self.detail_proj_b, pad=0)
            h = h + d
        h = group_norm(h, self.out_gn_g, self.out_gn_b, groups=1)
        h = np.maximum(0.0, h)
        return conv2d_forward(h, self.out_w, self.out_b, pad=1)


def _avg_pool_2x2(x: np.ndarray) -> np.ndarray:
    B, C, H, W = x.shape
    if H % 2 or W % 2:
        # Pad if odd
        pad_h = 1 if H % 2 else 0
        pad_w = 1 if W % 2 else 0
        x = np.pad(x, ((0, 0), (0, 0), (0, pad_h), (0, pad_w)), mode="edge")
        B, C, H, W = x.shape
    return x.reshape(B, C, H // 2, 2, W // 2, 2).mean(axis=(3, 5))


def _upsample_2x2(x: np.ndarray) -> np.ndarray:
    B, C, H, W = x.shape
    return np.repeat(np.repeat(x, 2, axis=2), 2, axis=3)


def count_params_v3(model: NumpyUNetV3) -> int:
    return int(sum(arr.size for _, arr in model._param_specs))
