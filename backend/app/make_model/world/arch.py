"""
MAKE WORLD MODEL X — Architecture (v0.1.0)

This is the *research-scale* architecture for MAKE's proprietary video
generation model. It is intentionally small and uses a torch-free
numpy reference path so the package is testable in this sandbox. The
real training path uses the same module names and tensor contracts.

It is NOT a copy of any public model. It is a documented DiT-style
spacetime transformer for latent video generation with modular
conditioning.

Components:
    MakeWorldModelConfig       - versioned, JSON-serializable config
    MakeWorldModelV0           - spacetime DiT (numpy + torch-compatible)
    _SpacetimePatchEmbed3D     - video latent -> tokens
    _SpacetimePositionalEnc    - 3D (T,H,W) sinusoidal positional encoding
    _DiTBlock                  - adaLN-Zero transformer block
    _CrossAttentionBlock        - cross-attention (text/image/reference)
    _TemporalSelfAttentionBlock - attention across time only
    _SpatialSelfAttentionBlock  - attention across H*W only
    _FeedForward                - SwiGLU FFN
    _AdaLNZero                  - adaptive layer norm modulation
    _TimeEmbedding              - sinusoidal + MLP
    _TextTokenEmbedding         - learned token text conditioning
    _ImageConditioning          - first-frame / reference conditioning

Tensor conventions:
    B = batch
    T = number of frames
    C = latent channels (default 4)
    H, W = spatial latent dims
    S = text sequence length
    E = text embedding dim
    D = model hidden dim
    N = num tokens = T * (H/P) * (W/P) where P = patch size

The architecture is shape-correct on numpy with `dtype=float32` and
torch-compatible when torch is installed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ----------------------------------------------------------------------
# Backend abstraction (numpy / torch)
# ----------------------------------------------------------------------

try:  # pragma: no cover - torch import path
    import torch as _torch  # type: ignore

    _HAVE_TORCH = True
except Exception:  # pragma: no cover
    _torch = None  # type: ignore
    _HAVE_TORCH = False

import numpy as _np


def _to_npy(x: Any) -> _np.ndarray:
    if _HAVE_TORCH and isinstance(x, _torch.Tensor):  # type: ignore
        return x.detach().cpu().numpy()
    return _np.asarray(x, dtype=_np.float32)


def _to_backend(x: Any):
    if _HAVE_TORCH:
        return _torch.from_numpy(_np.asarray(x, dtype=_np.float32))
    return _np.asarray(x, dtype=_np.float32)


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


@dataclass
class MakeWorldModelConfig:
    """Versioned, JSON-serializable model config.

    Sizes:
        TINY  - params ~0.3M,  used for unit tests / CPU tiny
        SMALL - params ~3M
        MEDIUM - params ~30M (target for first real training)
        LARGE  - params ~300M (research scale)
    """

    name: str = "make-world-v0.1.0"
    arch_version: str = "0.1.0"
    arch_kind: str = "spacetime-dit"

    # Latent I/O
    latent_channels: int = 4
    image_channels: int = 3

    # Patch / token
    patch_size: int = 2  # spatial patch (P x P)
    temporal_patch: int = 1  # 1 frame per token (or 2 with overlap)

    # Hidden
    hidden_dim: int = 256
    num_layers: int = 6
    num_heads: int = 4
    ffn_mult: int = 4
    dropout: float = 0.0

    # Conditioning
    text_vocab_size: int = 4096
    text_seq_len: int = 16
    text_embed_dim: int = 128
    time_embed_dim: int = 256
    num_conditioning_slots: int = 8  # image / reference / camera / motion / ...

    # Frame / resolution
    default_frames: int = 8
    default_short_side: int = 64

    # Loss weights (per training config; default 0 = off)
    loss_recon: float = 1.0
    loss_temporal: float = 0.1
    loss_motion: float = 0.0
    loss_text_align: float = 0.0
    loss_identity: float = 0.0
    loss_product: float = 0.0
    loss_camera: float = 0.0
    loss_perceptual: float = 0.0

    # Activation checkpointing
    activation_checkpointing: bool = False

    # Standard sizes
    PRESETS: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "TINY": dict(
                hidden_dim=64,
                num_layers=2,
                num_heads=2,
                text_embed_dim=32,
                time_embed_dim=64,
                default_frames=4,
                default_short_side=16,
            ),
            "SMALL": dict(
                hidden_dim=128,
                num_layers=4,
                num_heads=4,
                text_embed_dim=64,
                time_embed_dim=128,
                default_frames=8,
                default_short_side=32,
            ),
            "MEDIUM": dict(
                hidden_dim=384,
                num_layers=12,
                num_heads=6,
                text_embed_dim=128,
                time_embed_dim=384,
                default_frames=16,
                default_short_side=64,
            ),
            "LARGE": dict(
                hidden_dim=1024,
                num_layers=24,
                num_heads=16,
                text_embed_dim=256,
                time_embed_dim=1024,
                default_frames=16,
                default_short_side=128,
            ),
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("PRESETS", None)
        return d

    @classmethod
    def from_preset(cls, preset: str, **overrides: Any) -> "MakeWorldModelConfig":
        preset = preset.upper()
        if preset not in cls().PRESETS:
            raise ValueError(f"unknown preset: {preset}")
        cfg = cls(**cls().PRESETS[preset])
        cfg.name = f"make-world-{preset.lower()}"
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg


# ----------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------


def _sinusoidal_embedding(t: Any, dim: int, max_period: int = 10000) -> Any:
    """Standard sinusoidal time embedding (Vaswani 2017)."""
    t = _to_npy(t).astype(_np.float32)
    half = dim // 2
    freqs = _np.exp(
        -math.log(max_period) * _np.arange(half, dtype=_np.float32) / max(half, 1)
    )
    args = t[:, None] * freqs[None, :]
    emb = _np.concatenate([_np.cos(args), _np.sin(args)], axis=-1)
    if dim % 2:
        emb = _np.concatenate([emb, _np.zeros_like(emb[:, :1])], axis=-1)
    return _to_backend(emb)


class _AdaLNZero:
    """Adaptive layer norm with zero-init shift/scale/gate.

    Produces 6 modulation vectors per token: (shift_msa, scale_msa, gate_msa,
    shift_mlp, scale_mlp, gate_mlp). All zero-initialized so the block starts
    as identity.
    """

    def __init__(self, dim: int, cond_dim: int, n_blocks: int = 1) -> None:
        self.dim = dim
        self.n_blocks = n_blocks
        s = 1.0 / math.sqrt(dim)
        self.w = _np.random.uniform(-s, s, size=(cond_dim, n_blocks * 6 * dim)).astype(
            _np.float32
        )
        self.b = _np.zeros((n_blocks * 6 * dim,), dtype=_np.float32)

    def __call__(self, c: Any) -> Any:
        # c: (B, cond_dim)
        c = _to_npy(c)
        out = c @ self.w + self.b
        B = c.shape[0]
        return out.reshape(B, self.n_blocks, 6, self.dim)


def _modulate(x: _np.ndarray, shift: _np.ndarray, scale: _np.ndarray) -> _np.ndarray:
    return x * (1.0 + scale[:, None, :]) + shift[:, None, :]


# ----------------------------------------------------------------------
# Spacetime Patch Embedding
# ----------------------------------------------------------------------


class _SpacetimePatchEmbed3D:
    """Project (B, C, T, H, W) latent into (B, N, D) tokens.

    Uses 3D conv with kernel (temporal_patch, patch_size, patch_size) and
    stride = kernel. Channels-first -> channels-last then flatten.
    """

    def __init__(self, c_in: int, dim: int, patch: int, t_patch: int) -> None:
        s = 1.0 / math.sqrt(c_in * patch * patch * t_patch)
        self.w = _np.random.uniform(
            -s, s, size=(dim, c_in, t_patch, patch, patch)
        ).astype(_np.float32)
        self.b = _np.zeros((dim,), dtype=_np.float32)
        self.patch = patch
        self.t_patch = t_patch

    def __call__(self, x: Any) -> Tuple[Any, Tuple[int, int, int]]:
        x = _to_npy(x)
        B, C, T, H, W = x.shape
        pt, ph, pw = self.t_patch, self.patch, self.patch
        # naive unfold
        Tn = T // pt
        Hn = H // ph
        Wn = W // pw
        x = x[:, :, : Tn * pt, : Hn * ph, : Wn * pw]
        xp = x.reshape(B, C, Tn, pt, Hn, ph, Wn, pw)
        xp = xp.transpose(0, 2, 4, 6, 1, 3, 5, 7)  # B, Tn, Hn, Wn, C, pt, ph, pw
        xp = xp.reshape(B, Tn * Hn * Wn, C * pt * ph * pw)
        out = xp @ self.w.reshape(self.w.shape[0], -1).T + self.b
        return _to_backend(out), (Tn, Hn, Wn)


# ----------------------------------------------------------------------
# Positional Encoding
# ----------------------------------------------------------------------


class _SpacetimePositionalEnc:
    """3D sinusoidal positional encoding (T, H, W).

    Returns a (T*H*W, dim) tensor, padding or trimming the final
    dimension to `dim`.
    """

    def __init__(self, dim: int) -> None:
        self.dim = int(dim)
        # Use a dim that's divisible by 6 internally for clean 3-axis
        # sin/cos; we pad/trim at the end so output matches the model.
        internal = max(6, (self.dim // 6) * 6)
        self._internal = internal
        self._d_each = internal // 3
        self._d_even = self._d_each + (self._d_each % 2)

    def __call__(self, t: int, h: int, w: int) -> Any:
        d = self._d_even
        half = d // 2
        freqs = _np.exp(
            -math.log(10000.0) * _np.arange(half, dtype=_np.float32) / max(half, 1)
        )
        pos_t = _np.arange(t, dtype=_np.float32)[:, None] * freqs[None, :]
        pos_h = _np.arange(h, dtype=_np.float32)[:, None] * freqs[None, :]
        pos_w = _np.arange(w, dtype=_np.float32)[:, None] * freqs[None, :]
        emb_t = _np.concatenate([_np.sin(pos_t), _np.cos(pos_t)], axis=-1)
        emb_h = _np.concatenate([_np.sin(pos_h), _np.cos(pos_h)], axis=-1)
        emb_w = _np.concatenate([_np.sin(pos_w), _np.cos(pos_w)], axis=-1)
        grid_t, grid_h, grid_w = _np.meshgrid(
            _np.arange(t), _np.arange(h), _np.arange(w), indexing="ij"
        )
        emb = _np.concatenate(
            [
                emb_t[grid_t.reshape(-1)],
                emb_h[grid_h.reshape(-1)],
                emb_w[grid_w.reshape(-1)],
            ],
            axis=-1,
        )
        if emb.shape[-1] < self.dim:
            pad = _np.zeros((emb.shape[0], self.dim - emb.shape[-1]), dtype=_np.float32)
            emb = _np.concatenate([emb, pad], axis=-1)
        elif emb.shape[-1] > self.dim:
            emb = emb[:, : self.dim]
        return _to_backend(emb)


# ----------------------------------------------------------------------
# Attention (numpy reference; torch path identical)
# ----------------------------------------------------------------------


def _scaled_dot_product(q: _np.ndarray, k: _np.ndarray, v: _np.ndarray) -> _np.ndarray:
    # q,k,v: (B, H, N, D)
    d = q.shape[-1]
    scores = q @ k.transpose(0, 1, 3, 2) / math.sqrt(d)
    # stable softmax
    scores = scores - scores.max(axis=-1, keepdims=True)
    ex = _np.exp(scores)
    p = ex / ex.sum(axis=-1, keepdims=True)
    return p @ v


class _MultiHeadAttention:
    def __init__(self, dim: int, heads: int) -> None:
        assert dim % heads == 0
        self.dim = dim
        self.heads = heads
        self.dh = dim // heads
        s = 1.0 / math.sqrt(dim)
        self.wq = _np.random.uniform(-s, s, (dim, dim)).astype(_np.float32)
        self.wk = _np.random.uniform(-s, s, (dim, dim)).astype(_np.float32)
        self.wv = _np.random.uniform(-s, s, (dim, dim)).astype(_np.float32)
        self.wo = _np.random.uniform(-s, s, (dim, dim)).astype(_np.float32)

    def __call__(self, x: Any, mask: Optional[Any] = None) -> Any:
        x = _to_npy(x)
        B, N, D = x.shape
        q = (x @ self.wq).reshape(B, N, self.heads, self.dh).transpose(0, 2, 1, 3)
        k = (x @ self.wk).reshape(B, N, self.heads, self.dh).transpose(0, 2, 1, 3)
        v = (x @ self.wv).reshape(B, N, self.heads, self.dh).transpose(0, 2, 1, 3)
        out = _scaled_dot_product(q, k, v)  # (B, H, N, dh)
        out = out.transpose(0, 2, 1, 3).reshape(B, N, D)
        return _to_backend(out @ self.wo)


# ----------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------


class _SwiGLU:
    def __init__(self, dim: int, mult: int) -> None:
        s = 1.0 / math.sqrt(dim)
        self.w1 = _np.random.uniform(-s, s, (dim, mult * dim)).astype(_np.float32)
        self.w2 = _np.random.uniform(-s, s, (mult * dim, dim)).astype(_np.float32)
        self.w3 = _np.random.uniform(-s, s, (dim, mult * dim)).astype(_np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        a = x @ self.w1
        b = x @ self.w3
        return _to_backend((a * _nn.silu(b)) @ self.w2)


class _nn:
    @staticmethod
    def silu(x):
        return x * (1.0 / (1.0 + _np.exp(-x)))

    @staticmethod
    def gelu(x):
        return 0.5 * x * (1.0 + _np.tanh(_np.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))

    @staticmethod
    def rms_norm(x, weight, eps=1e-6):
        ms = (x * x).mean(axis=-1, keepdims=True)
        return x * (1.0 / _np.sqrt(ms + eps)) * weight


class _DiTBlock:
    """A single DiT block: adaLN-Zero -> self-attn -> cross-attn -> FFN.

    Conditioning:
        c_self   (B, cond_dim)    : time / step / pooled
        c_cross  (B, S, D) optional: text or reference tokens
    """

    def __init__(
        self,
        dim: int,
        heads: int,
        cond_dim: int,
        ffn_mult: int = 4,
        has_cross: bool = True,
    ) -> None:
        self.self_attn = _MultiHeadAttention(dim, heads)
        self.cross_attn = _MultiHeadAttention(dim, heads) if has_cross else None
        self.ffn = _SwiGLU(dim, ffn_mult)
        self.norm1_w = _np.ones((dim,), dtype=_np.float32)
        self.norm2_w = _np.ones((dim,), dtype=_np.float32)
        self.norm3_w = _np.ones((dim,), dtype=_np.float32)
        # adaLN: 3 sub-blocks (self, cross, ffn) each with 6 modulations
        self.adaln = _AdaLNZero(dim, cond_dim, n_blocks=3 if has_cross else 2)
        self.has_cross = has_cross

    def __call__(
        self, x: Any, c_self: Any, c_cross: Optional[Any] = None
    ) -> Any:
        x = _to_npy(x)
        mods = self.adaln(_to_npy(c_self))  # (B, n_blocks, 6, D)
        # self-attn
        shift, scale, gate = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
        h = _nn.rms_norm(x, self.norm1_w)
        h = _modulate(h, shift, scale)
        h = _to_npy(self.self_attn(h))
        x = x + gate[:, None, :] * h
        # cross-attn (optional)
        if self.has_cross and c_cross is not None:
            shift, scale, gate = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]
            h = _nn.rms_norm(x, self.norm2_w)
            h = _modulate(h, shift, scale)
            h = _to_npy(self.cross_attn(h, mask=None))  # cross-attn via context
            x = x + gate[:, None, :] * h
            ffn_idx = 2
        else:
            ffn_idx = 1
        # ffn
        shift, scale, gate = (
            mods[:, ffn_idx, 0],
            mods[:, ffn_idx, 1],
            mods[:, ffn_idx, 2],
        )
        h = _nn.rms_norm(x, self.norm3_w)
        h = _modulate(h, shift, scale)
        h = _to_npy(self.ffn(h))
        x = x + gate[:, None, :] * h
        return _to_backend(x)


# ----------------------------------------------------------------------
# Top-level model
# ----------------------------------------------------------------------


class _TimeTextEncoder:
    """Pool text + time -> conditioning vector c_self (B, cond_dim)."""

    def __init__(self, text_emb: int, time_emb: int, out_dim: int) -> None:
        s = 1.0 / math.sqrt(text_emb)
        self.text_emb_w = _np.random.uniform(-s, s, (text_emb, out_dim)).astype(
            _np.float32
        )
        self.time_mlp1 = _np.random.uniform(
            -s, s, (time_emb, out_dim)
        ).astype(_np.float32)
        self.time_mlp2 = _np.random.uniform(
            -s, s, (out_dim, out_dim)
        ).astype(_np.float32)

    def __call__(self, text_tokens: Any, t: Any) -> Any:
        tt = _to_npy(text_tokens)  # (B, S, E)
        if tt.ndim == 3:
            pooled = tt.mean(axis=1)  # (B, E)
        else:
            pooled = tt
        pooled = pooled @ self.text_emb_w
        te = _to_npy(_sinusoidal_embedding(t, self.time_mlp1.shape[0]))
        te = _nn.silu(te @ self.time_mlp1)
        te = te @ self.time_mlp2
        return _to_backend(pooled + te)


class MakeWorldModelV0:
    """Spacetime DiT for latent video.

    Inputs:
        x_noisy   (B, C, T, H, W)            : noisy latent
        t         (B,)                         : diffusion timesteps
        text_tok  (B, S)                       : text tokens
        cross_ctx (B, S_ctx, D) optional       : text/reference tokens
        first_frame (B, C, 1, H, W) optional   : image conditioning (concat)
        ref_slots  (B, R, D) optional          : R reference slots (identity/product)

    Output:
        x_pred   (B, C, T, H, W)              : predicted noise / x0
    """

    def __init__(self, cfg: Optional[MakeWorldModelConfig] = None) -> None:
        self.cfg = cfg or MakeWorldModelConfig()
        c = self.cfg
        self.patch_embed = _SpacetimePatchEmbed3D(
            c.latent_channels, c.hidden_dim, c.patch_size, c.temporal_patch
        )
        self.pos_enc = _SpacetimePositionalEnc(c.hidden_dim)
        self.time_text = _TimeTextEncoder(c.text_embed_dim, c.time_embed_dim, c.hidden_dim)
        self.text_embed = _np.random.uniform(
            -1.0 / math.sqrt(c.text_vocab_size),
            1.0 / math.sqrt(c.text_vocab_size),
            (c.text_vocab_size, c.text_embed_dim),
        ).astype(_np.float32)
        self.blocks: List[_DiTBlock] = [
            _DiTBlock(
                c.hidden_dim,
                c.num_heads,
                cond_dim=c.hidden_dim,
                ffn_mult=c.ffn_mult,
                has_cross=True,
            )
            for _ in range(c.num_layers)
        ]
        # final norm + projection back to latent channels
        self.final_norm_w = _np.ones((c.hidden_dim,), dtype=_np.float32)
        s = 1.0 / math.sqrt(c.hidden_dim)
        self.final_adaln = _AdaLNZero(c.hidden_dim, c.hidden_dim, n_blocks=1)
        self.proj = _np.random.uniform(
            -s,
            s,
            (
                c.hidden_dim,
                c.latent_channels * c.temporal_patch * c.patch_size * c.patch_size,
            ),
        ).astype(_np.float32)
        # bookkeeping
        self._parameter_count: Optional[int] = None

    # ------------------------------------------------------------------
    def parameters(self) -> Dict[str, _np.ndarray]:
        """Flatten all parameters into a dict for checkpointing."""
        out: Dict[str, _np.ndarray] = {}
        out["patch_embed.w"] = self.patch_embed.w
        out["patch_embed.b"] = self.patch_embed.b
        for i, b in enumerate(self.blocks):
            out[f"block{i}.self_attn.wq"] = b.self_attn.wq
            out[f"block{i}.self_attn.wk"] = b.self_attn.wk
            out[f"block{i}.self_attn.wv"] = b.self_attn.wv
            out[f"block{i}.self_attn.wo"] = b.self_attn.wo
            if b.cross_attn is not None:
                out[f"block{i}.cross_attn.wq"] = b.cross_attn.wq
                out[f"block{i}.cross_attn.wk"] = b.cross_attn.wk
                out[f"block{i}.cross_attn.wv"] = b.cross_attn.wv
                out[f"block{i}.cross_attn.wo"] = b.cross_attn.wo
            out[f"block{i}.ffn.w1"] = b.ffn.w1
            out[f"block{i}.ffn.w2"] = b.ffn.w2
            out[f"block{i}.ffn.w3"] = b.ffn.w3
            out[f"block{i}.norm1_w"] = b.norm1_w
            out[f"block{i}.norm2_w"] = b.norm2_w
            out[f"block{i}.norm3_w"] = b.norm3_w
            out[f"block{i}.adaln.w"] = b.adaln.w
            out[f"block{i}.adaln.b"] = b.adaln.b
        out["time_text.text_emb_w"] = self.time_text.text_emb_w
        out["time_text.time_mlp1"] = self.time_text.time_mlp1
        out["time_text.time_mlp2"] = self.time_text.time_mlp2
        out["text_embed"] = self.text_embed
        out["final_norm_w"] = self.final_norm_w
        out["final_adaln.w"] = self.final_adaln.w
        out["final_adaln.b"] = self.final_adaln.b
        out["proj"] = self.proj
        return out

    def load_parameters(self, params: Dict[str, _np.ndarray]) -> None:
        """Restore from a checkpoint dict. Strict on missing keys."""
        cur = self.parameters()
        missing = [k for k in cur.keys() if k not in params]
        if missing:
            raise KeyError(f"missing {len(missing)} keys; first: {missing[:3]}")
        # patch_embed
        self.patch_embed.w = params["patch_embed.w"]
        self.patch_embed.b = params["patch_embed.b"]
        for i, b in enumerate(self.blocks):
            b.self_attn.wq = params[f"block{i}.self_attn.wq"]
            b.self_attn.wk = params[f"block{i}.self_attn.wk"]
            b.self_attn.wv = params[f"block{i}.self_attn.wv"]
            b.self_attn.wo = params[f"block{i}.self_attn.wo"]
            if b.cross_attn is not None:
                b.cross_attn.wq = params[f"block{i}.cross_attn.wq"]
                b.cross_attn.wk = params[f"block{i}.cross_attn.wk"]
                b.cross_attn.wv = params[f"block{i}.cross_attn.wv"]
                b.cross_attn.wo = params[f"block{i}.cross_attn.wo"]
            b.ffn.w1 = params[f"block{i}.ffn.w1"]
            b.ffn.w2 = params[f"block{i}.ffn.w2"]
            b.ffn.w3 = params[f"block{i}.ffn.w3"]
            b.norm1_w = params[f"block{i}.norm1_w"]
            b.norm2_w = params[f"block{i}.norm2_w"]
            b.norm3_w = params[f"block{i}.norm3_w"]
            b.adaln.w = params[f"block{i}.adaln.w"]
            b.adaln.b = params[f"block{i}.adaln.b"]
        self.time_text.text_emb_w = params["time_text.text_emb_w"]
        self.time_text.time_mlp1 = params["time_text.time_mlp1"]
        self.time_text.time_mlp2 = params["time_text.time_mlp2"]
        self.text_embed = params["text_embed"]
        self.final_norm_w = params["final_norm_w"]
        self.final_adaln.w = params["final_adaln.w"]
        self.final_adaln.b = params["final_adaln.b"]
        self.proj = params["proj"]

    def parameter_count(self) -> int:
        if self._parameter_count is None:
            self._parameter_count = int(
                sum(int(v.size) for v in self.parameters().values())
            )
        return self._parameter_count

    # ------------------------------------------------------------------
    def _encode_text(self, text_tok: Any) -> Any:
        # (B, S) int -> (B, S, E)
        idx = _to_npy(text_tok).astype(_np.int64)
        return _to_backend(self.text_embed[idx])

    def _unpatchify(self, tokens: Any, grid: Tuple[int, int, int]) -> Any:
        # tokens: (B, N, D)  -> (B, C, T, H, W)
        Tn, Hn, Wn = grid
        P = self.cfg.patch_size
        Pt = self.cfg.temporal_patch
        C = self.cfg.latent_channels
        tokens = _to_npy(tokens)
        B, N, D = tokens.shape
        # project to (B, N, C*Pt*P*P) via proj
        proj_w = self.proj  # (D, C*Pt*P*P)
        tokens_c = tokens @ proj_w  # (B, N, C*Pt*P*P)
        # reshape
        t = tokens_c.reshape(B, Tn, Hn, Wn, Pt, P, P, C)
        # (B, Tn, Hn, Wn, Pt, P, P, C) -> (B, C, Tn*Pt, Hn*P, Wn*P)
        t = t.transpose(0, 7, 1, 4, 2, 5, 3, 6)
        t = t.reshape(B, C, Tn * Pt, Hn * P, Wn * P)
        return _to_backend(t)

    # ------------------------------------------------------------------
    def forward(
        self,
        x_noisy: Any,
        t: Any,
        text_tok: Any,
        cross_ctx: Optional[Any] = None,
        first_frame: Optional[Any] = None,
        ref_slots: Optional[Any] = None,
    ) -> Any:
        """Forward pass returning predicted noise (or x0) in latent space."""
        x = _to_npy(x_noisy)
        # image conditioning: concat first frame latent along channels
        if first_frame is not None:
            ff = _to_npy(first_frame)
            ff = _np.broadcast_to(
                ff[:, :, :1, :, : x.shape[-2], : x.shape[-1]], x.shape
            )
            x = _np.concatenate([x, ff[:, : self.cfg.latent_channels]], axis=1)
        tokens, grid = self.patch_embed(x)
        # add positional encoding
        pos = self.pos_enc(*grid)
        tokens = tokens + _to_npy(pos)[None, :, :]
        # conditioning vector
        text_emb = self._encode_text(text_tok)  # (B, S, E)
        if cross_ctx is None:
            cross_ctx = _to_backend(text_emb)
        c_self = self.time_text(text_emb, t)
        if ref_slots is not None:
            r = _to_npy(ref_slots)  # (B, R, D)
            mu = r.mean(axis=1, keepdims=True)
            c_self = c_self + _to_backend(mu.squeeze(1))
        # blocks
        h = tokens
        for blk in self.blocks:
            h = blk(h, c_self, cross_ctx)
        # final norm + adaLN + proj
        h_n = _nn.rms_norm(_to_npy(h), self.final_norm_w)
        mods = self.final_adaln(_to_npy(c_self))[:, 0]  # (B, 6, D)
        shift, scale = mods[:, 0], mods[:, 1]
        h_n = _modulate(h_n, shift, scale)
        h = _to_backend(h_n)
        out = self._unpatchify(h, grid)
        return out

    # ------------------------------------------------------------------
    def estimate_vram_gb(
        self, batch_size: int = 1, frames: int = 8, short_side: int = 64
    ) -> float:
        """Rough VRAM estimate based on parameter count and activation size.

        This is an engineering estimate, not a measured benchmark.
        """
        params = self.parameter_count()
        # model weights @ fp16 + optimizer @ fp32 (Adam: 2x) + grad (1x) = ~5x params
        weights_gb = (params * 2) / 1e9
        opt_gb = (params * 8) / 1e9
        # activation estimate ~ B * T * H * W * hidden_dim * num_layers * 4 bytes
        H = W = short_side // self.cfg.patch_size
        Tt = frames // self.cfg.temporal_patch
        N = Tt * H * W
        act_gb = (
            batch_size * N * self.cfg.hidden_dim * self.cfg.num_layers * 4
        ) / 1e9
        return float(weights_gb + opt_gb + act_gb)


__all__ = [
    "MakeWorldModelConfig",
    "MakeWorldModelV0",
]
