"""MAKE Image Engine — Core Architecture.

Foundation model architecture for MAKE-native image intelligence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import torch as _torch
    import torch.nn as _nn
    import torch.nn.functional as _F
    _HAVE_TORCH = True
except Exception:
    _torch = None  # type: ignore
    _nn = None  # type: ignore
    _F = None  # type: ignore
    _HAVE_TORCH = False


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


@dataclass
class ImageConfig:
    name: str = "make-image-v0.1.0"
    arch_version: str = "0.1.0"
    arch_kind: str = "make-image-dit"

    latent_channels: int = 4
    image_channels: int = 3
    patch_size: int = 2
    hidden_dim: int = 256
    num_layers: int = 6
    num_heads: int = 4
    ffn_mult: int = 4
    dropout: float = 0.0
    text_vocab_size: int = 4096
    text_seq_len: int = 16
    text_embed_dim: int = 128
    time_embed_dim: int = 256
    identity_dim: int = 256
    object_dim: int = 256
    scene_dim: int = 256
    spatial_dim: int = 128
    default_short_side: int = 64
    default_frames: int = 1
    use_rope: bool = True
    use_qk_norm: bool = True
    use_gradient_checkpointing: bool = False

    PRESETS: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "TINY": dict(
                hidden_dim=64, num_layers=2, num_heads=2,
                text_embed_dim=32, time_embed_dim=64,
                identity_dim=32, object_dim=32, scene_dim=32,
                default_short_side=32,
            ),
            "SMALL": dict(
                hidden_dim=128, num_layers=4, num_heads=4,
                text_embed_dim=64, time_embed_dim=128,
                identity_dim=64, object_dim=64, scene_dim=64,
                default_short_side=64,
            ),
            "MEDIUM": dict(
                hidden_dim=384, num_layers=12, num_heads=6,
                text_embed_dim=128, time_embed_dim=384,
                identity_dim=128, object_dim=128, scene_dim=128,
                default_short_side=128,
            ),
            "LARGE": dict(
                hidden_dim=1024, num_layers=24, num_heads=16,
                text_embed_dim=256, time_embed_dim=1024,
                identity_dim=256, object_dim=256, scene_dim=256,
                default_short_side=256,
            ),
            "PRODUCTION": dict(
                hidden_dim=2048, num_layers=30, num_heads=16,
                ffn_mult=4, text_embed_dim=1024, time_embed_dim=2048,
                identity_dim=1024, object_dim=1024, scene_dim=1024,
                default_short_side=256, use_rope=True, use_qk_norm=True,
                use_gradient_checkpointing=True,
            ),
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d.pop("PRESETS", None)
        return d

    @classmethod
    def from_preset(cls, preset: str, **overrides: Any) -> "ImageConfig":
        preset = preset.upper()
        if preset not in cls().PRESETS:
            raise ValueError(f"unknown preset: {preset}")
        cfg = cls(**cls().PRESETS[preset])
        cfg.name = f"make-image-{preset.lower()}"
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg


# ----------------------------------------------------------------------
# Backend utilities
# ----------------------------------------------------------------------


def _to_npy(x: Any) -> np.ndarray:
    if _HAVE_TORCH and isinstance(x, _torch.Tensor):
        return x.detach().cpu().numpy()
    return np.asarray(x, dtype=np.float32)


def _to_backend(x: Any):
    if _HAVE_TORCH:
        return _torch.from_numpy(np.asarray(x, dtype=np.float32))
    return np.asarray(x, dtype=np.float32)


# ----------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------


class _SinusoidalEmbedding:
    def __init__(self, dim: int, max_period: int = 10000) -> None:
        self.dim = dim
        self.max_period = max_period

    def __call__(self, t: Any) -> Any:
        t = _to_npy(t).astype(np.float32)
        half = self.dim // 2
        freqs = np.exp(-np.log(self.max_period) * np.arange(half, dtype=np.float32) / max(half, 1))
        args = t[:, None] * freqs[None, :]
        emb = np.concatenate([np.cos(args), np.sin(args)], axis=-1)
        if self.dim % 2:
            emb = np.concatenate([emb, np.zeros_like(emb[:, :1])], axis=-1)
        return _to_backend(emb)


class _RMSNorm:
    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        self.dim = dim
        self.eps = eps
        self.weight = np.ones((dim,), dtype=np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        ms = (x * x).mean(axis=-1, keepdims=True)
        return _to_backend(x * (self.weight / np.sqrt(ms + self.eps)))


class _LayerNorm:
    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        self.dim = dim
        self.eps = eps
        self.weight = np.ones((dim,), dtype=np.float32)
        self.bias = np.zeros((dim,), dtype=np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        ms = (x * x).mean(axis=-1, keepdims=True)
        x = x / np.sqrt(ms + self.eps)
        return _to_backend(x * self.weight + self.bias)


class _GroupNorm3D:
    def __init__(self, ch: int, groups: int = 8) -> None:
        self.groups = min(groups, ch)
        self.ch_per_group = ch // self.groups
        self.weight = np.ones((ch,), dtype=np.float32)
        self.bias = np.zeros((ch,), dtype=np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        B, C = x.shape[0], x.shape[1]
        x = x.reshape(B, self.groups, self.ch_per_group, *x.shape[2:])
        ms = (x * x).mean(axis=tuple(range(2, x.ndim)), keepdims=True)
        x = x / np.sqrt(ms + 1e-6)
        x = x.reshape(B, C, *x.shape[3:])
        return _to_backend(x * self.weight[None, :, None, None, None] + self.bias[None, :, None, None, None])


class _SwiGLU:
    def __init__(self, dim: int, mult: int = 4) -> None:
        s = 1.0 / math.sqrt(dim)
        self.w1 = np.random.uniform(-s, s, (dim, mult * dim)).astype(np.float32)
        self.w2 = np.random.uniform(-s, s, (mult * dim, dim)).astype(np.float32)
        self.w3 = np.random.uniform(-s, s, (dim, mult * dim)).astype(np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        a = x @ self.w1
        b = x @ self.w3
        return _to_backend((a * (b / (1.0 + np.exp(-b)))) @ self.w2)


class _AdaLNZero:
    def __init__(self, dim: int, cond_dim: int, n_blocks: int = 1) -> None:
        self.dim = dim
        self.n_blocks = n_blocks
        s = 1.0 / math.sqrt(dim)
        self.w = np.random.uniform(-s, s, size=(cond_dim, n_blocks * 6 * dim)).astype(np.float32)
        self.b = np.zeros((n_blocks * 6 * dim,), dtype=np.float32)

    def __call__(self, c: Any) -> Any:
        c = _to_npy(c)
        B = c.shape[0]
        out = c @ self.w + self.b
        return _to_backend(out.reshape(B, self.n_blocks, 6, self.dim))


def _modulate(x: np.ndarray, shift: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return x * (1.0 + scale[:, None, :]) + shift[:, None, :]


class _MultiHeadAttention:
    def __init__(self, dim: int, heads: int) -> None:
        assert dim % heads == 0
        self.dim = dim
        self.heads = heads
        self.dh = dim // heads
        s = 1.0 / math.sqrt(dim)
        self.wq = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.wk = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.wv = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.wo = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)

    def __call__(self, x: Any, mask: Optional[Any] = None, kv: Optional[Any] = None) -> Any:
        x = _to_npy(x)
        B, N, D = x.shape
        q = (x @ self.wq).reshape(B, N, self.heads, self.dh).transpose(0, 2, 1, 3)
        k = (_to_npy(kv) @ self.wk if kv is not None else x @ self.wk).reshape(B, -1, self.heads, self.dh).transpose(0, 2, 1, 3)
        v = (_to_npy(kv) @ self.wv if kv is not None else x @ self.wv).reshape(B, -1, self.heads, self.dh).transpose(0, 2, 1, 3)
        scores = q @ k.transpose(0, 1, 3, 2) / math.sqrt(self.dh)
        if mask is not None:
            scores = scores + mask
        ex = np.exp(scores - scores.max(axis=-1, keepdims=True))
        p = ex / ex.sum(axis=-1, keepdims=True)
        out = p @ v
        out = out.transpose(0, 2, 1, 3).reshape(B, N, D)
        return _to_backend(out @ self.wo)


class _DiTBlock:
    def __init__(self, dim: int, heads: int, cond_dim: int, ffn_mult: int = 4, has_cross: bool = True, cross_dim: Optional[int] = None) -> None:
        self.self_attn = _MultiHeadAttention(dim, heads)
        self.cross_attn = _MultiHeadAttention(dim, heads) if has_cross else None
        self.ffn = _SwiGLU(dim, ffn_mult)
        self.norm1 = _RMSNorm(dim)
        self.norm2 = _RMSNorm(dim)
        self.norm3 = _RMSNorm(dim)
        self.adaln = _AdaLNZero(dim, cond_dim, n_blocks=3 if has_cross else 2)
        self.has_cross = has_cross
        self.cross_proj = np.random.uniform(-1e-5, 1e-5, (cross_dim or dim, dim)).astype(np.float32) if has_cross and cross_dim and cross_dim != dim else None

    def __call__(self, x: Any, c_self: Any, c_cross: Optional[Any] = None) -> Any:
        x = _to_npy(x)
        mods = _to_npy(self.adaln(c_self))
        if self.has_cross and c_cross is not None:
            shift_s, scale_s, gate_s = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
            shift_c, scale_c, gate_c = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]
            shift_f, scale_f, gate_f = mods[:, 2, 0], mods[:, 2, 1], mods[:, 2, 2]
        else:
            shift_s, scale_s, gate_s = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
            shift_f, scale_f, gate_f = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]

        h = _modulate(_to_npy(self.norm1(x)), shift_s, scale_s)
        x = x + gate_s[:, None, :] * _to_npy(self.self_attn(h))

        if self.has_cross and c_cross is not None:
            h = _modulate(_to_npy(self.norm2(x)), shift_c, scale_c)
            kv = _to_npy(c_cross) @ self.cross_proj if self.cross_proj is not None else _to_npy(c_cross)
            x = x + gate_c[:, None, :] * _to_npy(self.cross_attn(h, kv=kv))

        h = _modulate(_to_npy(self.norm3(x)), shift_f, scale_f)
        x = x + gate_f[:, None, :] * _to_npy(self.ffn(h))
        return _to_backend(x)


class _PatchEmbed2D:
    def __init__(self, c_in: int, dim: int, patch: int) -> None:
        self.patch = patch
        s = 1.0 / math.sqrt(c_in * patch * patch)
        self.w = np.random.uniform(-s, s, size=(dim, c_in, patch, patch)).astype(np.float32)
        self.b = np.zeros((dim,), dtype=np.float32)

    def __call__(self, x: Any) -> Tuple[Any, Tuple[int, int]]:
        x = _to_npy(x)
        B, C, H, W = x.shape
        ph = pw = self.patch
        Hn, Wn = H // ph, W // pw
        x = x[:, :, :Hn * ph, :Wn * pw]
        xp = x.reshape(B, C, Hn, ph, Wn, pw).transpose(0, 2, 4, 1, 3, 5).reshape(B, Hn * Wn, C * ph * pw)
        out = xp @ self.w.reshape(self.w.shape[0], -1).T + self.b
        return _to_backend(out), (Hn, Wn)


class _PositionalEnc2D:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def __call__(self, h: int, w: int) -> Any:
        internal = max(6, (self.dim // 6) * 6)
        d_each = internal // 2
        half = d_each // 2
        freqs = np.exp(-np.log(10000.0) * np.arange(half, dtype=np.float32) / max(half, 1))
        pos_h = np.arange(h, dtype=np.float32)[:, None] * freqs[None, :]
        pos_w = np.arange(w, dtype=np.float32)[:, None] * freqs[None, :]
        emb_h = np.concatenate([np.sin(pos_h), np.cos(pos_h)], axis=-1)
        emb_w = np.concatenate([np.sin(pos_w), np.cos(pos_w)], axis=-1)
        grid_h, grid_w = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        emb = np.concatenate([emb_h[grid_h.reshape(-1)], emb_w[grid_w.reshape(-1)], np.zeros((h * w, self.dim - emb_h.shape[-1] * 2), dtype=np.float32)], axis=-1)
        if emb.shape[-1] < self.dim:
            emb = np.pad(emb, ((0, 0), (0, self.dim - emb.shape[-1])))
        return _to_backend(emb[:, : self.dim])


class _ConditioningProjections:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        s = 1.0 / math.sqrt(dim)
        self.proj_text = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_image = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_identity = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_object = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_scene = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_camera = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_lighting = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_material = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)
        self.proj_world = np.random.uniform(-s, s, (dim, dim)).astype(np.float32)

    def __call__(self, bundle: Dict[str, Any]) -> Any:
        c = np.zeros((1, self.dim), dtype=np.float32)
        for name, proj in [
            ("text_emb", self.proj_text),
            ("image_emb", self.proj_image),
            ("identity_emb", self.proj_identity),
            ("object_emb", self.proj_object),
            ("scene_emb", self.proj_scene),
            ("camera_emb", self.proj_camera),
            ("lighting_emb", self.proj_lighting),
            ("material_emb", self.proj_material),
            ("world_emb", self.proj_world),
        ]:
            val = bundle.get(name)
            if val is not None:
                v = _to_npy(val)
                if v.ndim == 1:
                    v = v[None, :]
                elif v.ndim == 3:
                    v = v.mean(axis=1)
                c = c + v @ proj
        return _to_backend(c)


class _TimeTextEncoder:
    def __init__(self, text_emb: int, time_emb: int, out_dim: int) -> None:
        s = 1.0 / math.sqrt(text_emb)
        self.text_emb_w = np.random.uniform(-s, s, (text_emb, out_dim)).astype(np.float32)
        self.time_mlp1 = np.random.uniform(-s, s, (time_emb, out_dim)).astype(np.float32)
        self.time_mlp2 = np.random.uniform(-s, s, (out_dim, out_dim)).astype(np.float32)

    def __call__(self, text_tokens: Any, t: Any) -> Any:
        tt = _to_npy(text_tokens)
        if tt.ndim == 3:
            pooled = tt.mean(axis=1)
        else:
            pooled = tt
        te = _SinusoidalEmbedding(self.time_mlp1.shape[0])(t)
        te = te @ self.time_mlp1
        te = _to_npy(te) * (1.0 / (1.0 + np.exp(-_to_npy(te))))
        te = te @ self.time_mlp2
        return _to_backend(pooled @ self.text_emb_w + te)


# ----------------------------------------------------------------------
# Foundation model
# ----------------------------------------------------------------------


class ImageFoundationModel:
    def __init__(self, cfg: Optional[ImageConfig] = None) -> None:
        self.cfg = cfg or ImageConfig()
        c = self.cfg
        dim = c.hidden_dim

        self.patch_embed = _PatchEmbed2D(c.image_channels, dim, c.patch_size)
        self.pos_enc = _PositionalEnc2D(dim)
        self.time_text = _TimeTextEncoder(c.text_embed_dim, c.time_embed_dim, dim)
        s_emb = 1.0 / math.sqrt(c.text_vocab_size)
        self.text_embed = np.random.uniform(-s_emb, s_emb, (c.text_vocab_size, c.text_embed_dim)).astype(np.float32)
        self.blocks = [_DiTBlock(dim, c.num_heads, dim, c.ffn_mult, has_cross=True, cross_dim=c.text_embed_dim) for _ in range(c.num_layers)]
        self.final_norm = _RMSNorm(dim)
        self.final_adaln = _AdaLNZero(dim, dim, n_blocks=1)
        s = 1.0 / math.sqrt(dim)
        self.proj = np.random.uniform(-s, s, (dim, c.latent_channels * c.patch_size * c.patch_size)).astype(np.float32)
        self.conditioning_projections = _ConditioningProjections(dim)
        dec_in = c.latent_channels * c.patch_size * c.patch_size
        self.dec_proj = np.random.uniform(-s, s, (dec_in, dim)).astype(np.float32)
        self.dec_out = np.random.uniform(-s, s, (dim, c.image_channels * c.patch_size * c.patch_size)).astype(np.float32)
        self._parameter_count: Optional[int] = None
        self._torch_model: Optional[Any] = None

    def parameters(self) -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
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
            out[f"block{i}.norm1.weight"] = b.norm1.weight
            out[f"block{i}.norm2.weight"] = b.norm2.weight
            out[f"block{i}.norm3.weight"] = b.norm3.weight
            out[f"block{i}.adaln.w"] = b.adaln.w
            out[f"block{i}.adaln.b"] = b.adaln.b
            if b.cross_proj is not None:
                out[f"block{i}.cross_proj"] = b.cross_proj
        out["time_text.text_emb_w"] = self.time_text.text_emb_w
        out["time_text.time_mlp1"] = self.time_text.time_mlp1
        out["time_text.time_mlp2"] = self.time_text.time_mlp2
        out["text_embed"] = self.text_embed
        out["final_norm.weight"] = self.final_norm.weight
        out["final_adaln.w"] = self.final_adaln.w
        out["final_adaln.b"] = self.final_adaln.b
        out["proj"] = self.proj
        out["dec_proj"] = self.dec_proj
        out["dec_out"] = self.dec_out
        for name, proj in self.conditioning_projections.__dict__.items():
            if hasattr(proj, "shape"):
                out[f"cond_proj.{name}"] = proj
        return out

    def load_parameters(self, params: Dict[str, np.ndarray]) -> None:
        cur = self.parameters()
        missing = [k for k in cur.keys() if k not in params]
        if missing:
            raise KeyError(f"missing {len(missing)} keys; first: {missing[:3]}")
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
            b.norm1.weight = params[f"block{i}.norm1.weight"]
            b.norm2.weight = params[f"block{i}.norm2.weight"]
            b.norm3.weight = params[f"block{i}.norm3.weight"]
            b.adaln.w = params[f"block{i}.adaln.w"]
            b.adaln.b = params[f"block{i}.adaln.b"]
            if b.cross_proj is not None and f"block{i}.cross_proj" in params:
                b.cross_proj = params[f"block{i}.cross_proj"]
        self.time_text.text_emb_w = params["time_text.text_emb_w"]
        self.time_text.time_mlp1 = params["time_text.time_mlp1"]
        self.time_text.time_mlp2 = params["time_text.time_mlp2"]
        self.text_embed = params["text_embed"]
        self.final_norm.weight = params["final_norm.weight"]
        self.final_adaln.w = params["final_adaln.w"]
        self.final_adaln.b = params["final_adaln.b"]
        self.proj = params["proj"]
        self.dec_proj = params["dec_proj"]
        self.dec_out = params["dec_out"]
        self._parameter_count = None

    def parameter_count(self) -> int:
        if self._parameter_count is None:
            self._parameter_count = int(sum(int(v.size) for v in self.parameters().values()))
        return self._parameter_count

    def forward(
        self,
        x_noisy: Any,
        t: Any,
        text_tok: Any,
        cross_ctx: Optional[Any] = None,
        conditioning: Optional[Dict[str, Any]] = None,
    ) -> Any:
        x = _to_npy(x_noisy)
        tokens, grid = self.patch_embed(x)
        pos = self.pos_enc(*grid)
        tokens = tokens + _to_npy(pos)[None, :, :]
        text_emb = self._encode_text(text_tok)
        if cross_ctx is None:
            cross_ctx = _to_backend(text_emb)
        c_self = self.time_text(text_emb, t)
        if conditioning is not None:
            c_self = c_self + _to_npy(self.conditioning_projections(conditioning))
        h = tokens
        for blk in self.blocks:
            h = blk(h, c_self, cross_ctx)
        h_n = _to_npy(self.final_norm(h))
        mods = _to_npy(self.final_adaln(c_self))[:, 0]
        shift, scale = mods[:, 0], mods[:, 1]
        h_n = _modulate(h_n, shift, scale)
        h = _to_backend(h_n)
        out = h @ self.proj
        B, N, _ = out.shape
        Hn, Wn = grid
        P = self.cfg.patch_size
        C = self.cfg.latent_channels
        out = out.reshape(B, Hn, Wn, P, P, C)
        out = np.transpose(out, (0, 5, 1, 3, 2, 4)).reshape(B, C, Hn * P, Wn * P)
        return _to_backend(out)

    def decode(self, latent: Any) -> Any:
        x = _to_npy(latent)
        B, C, H, W = x.shape
        P = self.cfg.patch_size
        Hn, Wn = H // P, W // P
        x = x[:, :, :Hn * P, :Wn * P]
        xp = x.reshape(B, C, Hn, P, Wn, P).transpose(0, 2, 4, 1, 3, 5).reshape(B, Hn * Wn, C * P * P)
        h = xp @ self.dec_proj
        h = _to_backend(h)
        h_n = _to_npy(_RMSNorm(h.shape[-1])(h))
        mods = _to_npy(self.final_adaln(_to_backend(np.zeros((B, self.cfg.hidden_dim), dtype=np.float32))))[:, 0]
        shift, scale = mods[:, 0], mods[:, 1]
        h_n = _modulate(h_n, shift, scale)
        h = _to_backend(h_n)
        out = h @ self.dec_out
        out = out.reshape(B, Hn, Wn, P, P, self.cfg.image_channels).transpose(0, 5, 1, 3, 2, 4).reshape(B, self.cfg.image_channels, Hn * P, Wn * P)
        return _to_backend(out)

    def _encode_text(self, text_tok: Any) -> Any:
        idx = _to_npy(text_tok).astype(np.int64)
        return _to_backend(self.text_embed[idx])

    def _build_torch_model(self) -> Any:
        if not _HAVE_TORCH:
            return None
        if self._torch_model is not None:
            return self._torch_model

        c = self.cfg
        dim = c.hidden_dim

        class _TorchDiT(_nn.Module):
            def __init__(self, outer: "ImageFoundationModel"):
                super().__init__()
                self.outer = outer
                self.cfg = c
                self.patch_embed = _nn.Conv2d(c.image_channels, dim, kernel_size=c.patch_size, stride=c.patch_size, bias=True)
                self.time_text = _nn.Sequential(
                    _nn.Linear(c.time_embed_dim, dim),
                    _nn.SiLU(),
                    _nn.Linear(dim, dim),
                )
                self.text_embed = _nn.Embedding(c.text_vocab_size, c.text_embed_dim)
                self.text_proj = _nn.Linear(c.text_embed_dim, dim, bias=False)
                self.blocks = _nn.ModuleList()
                for _ in range(c.num_layers):
                    block = _nn.ModuleDict({
                        "self_attn": _nn.ModuleDict({
                            "wq": _nn.Linear(dim, dim, bias=False),
                            "wk": _nn.Linear(dim, dim, bias=False),
                            "wv": _nn.Linear(dim, dim, bias=False),
                            "wo": _nn.Linear(dim, dim, bias=False),
                        }),
                        "cross_attn": _nn.ModuleDict({
                            "wq": _nn.Linear(dim, dim, bias=False),
                            "wk": _nn.Linear(dim, dim, bias=False),
                            "wv": _nn.Linear(dim, dim, bias=False),
                            "wo": _nn.Linear(dim, dim, bias=False),
                        }),
                        "ffn": _nn.ModuleDict({
                            "w1": _nn.Linear(dim, c.ffn_mult * dim, bias=False),
                            "w2": _nn.Linear(c.ffn_mult * dim, dim, bias=False),
                            "w3": _nn.Linear(dim, c.ffn_mult * dim, bias=False),
                        }),
                        "norm1": _nn.LayerNorm(dim, elementwise_affine=False),
                        "norm2": _nn.LayerNorm(dim, elementwise_affine=False),
                        "norm3": _nn.LayerNorm(dim, elementwise_affine=False),
                        "adaln": _nn.Linear(dim, 6 * dim * 3),
                        "cross_proj": _nn.Linear(c.text_embed_dim, dim, bias=False) if c.text_embed_dim != dim else _nn.Identity(),
                    })
                    self.blocks.append(block)
                self.final_norm = _nn.LayerNorm(dim, elementwise_affine=False)
                self.final_adaln = _nn.Linear(dim, 6 * dim)
                self.proj = _nn.Linear(dim, c.latent_channels * c.patch_size * c.patch_size, bias=True)
                self.dec_proj = _nn.Linear(c.latent_channels * c.patch_size * c.patch_size, dim, bias=False)
                self.dec_out = _nn.Linear(dim, c.image_channels * c.patch_size * c.patch_size, bias=True)

            def _get_pe(self, h: int, w: int):
                return self.outer.pos_enc(h, w)

            def _modulate(self, x, shift, scale):
                return x * (1 + scale.unsqueeze(1)) + shift.unsqueeze(1)

            def forward(self, x: _torch.Tensor, t: _torch.Tensor, text_tok: _torch.Tensor, cross_ctx: Optional[_torch.Tensor] = None, conditioning: Optional[Dict[str, Any]] = None) -> _torch.Tensor:
                B = x.shape[0]
                tokens = self.patch_embed(x).flatten(2).transpose(1, 2)
                h = tokens.shape[1]
                pos = self._get_pe(int(math.sqrt(h)), int(math.sqrt(h)))
                tokens = tokens + pos.to(x.device).unsqueeze(0)

                text_emb = self.text_embed(text_tok)
                if cross_ctx is None:
                    cross_ctx = text_emb

                half = c.time_embed_dim // 2
                freqs = _torch.exp(-_torch.log(_torch.tensor(10000.0)) * _torch.arange(half, device=t.device, dtype=t.dtype) / max(half, 1))
                args = t.unsqueeze(1) * freqs.unsqueeze(0)
                te = _torch.cat([_torch.cos(args), _torch.sin(args)], dim=-1)
                if te.shape[-1] < c.time_embed_dim:
                    te = _F.pad(te, (0, c.time_embed_dim - te.shape[-1]))
                te = self.time_text(te)
                c_self = self.text_proj(text_emb.mean(dim=1)) + te

                if conditioning is not None:
                    cond_vec = _torch.zeros((B, dim), device=x.device, dtype=x.dtype)
                    for key, proj_name in [
                        ("text_emb", "proj_text"),
                        ("image_emb", "proj_image"),
                        ("identity_emb", "proj_identity"),
                        ("object_emb", "proj_object"),
                        ("scene_emb", "proj_scene"),
                        ("camera_emb", "proj_camera"),
                        ("lighting_emb", "proj_lighting"),
                        ("material_emb", "proj_material"),
                        ("world_emb", "proj_world"),
                    ]:
                        val = conditioning.get(key)
                        if val is not None:
                            v = _torch.from_numpy(np.asarray(val, dtype=np.float32)).to(x.device)
                            if v.ndim == 1:
                                v = v.unsqueeze(0)
                            elif v.ndim == 3:
                                v = v.mean(dim=1)
                            proj_w = _torch.from_numpy(getattr(self.outer.conditioning_projections, proj_name)).to(x.device)
                            cond_vec = cond_vec + v @ proj_w
                    c_self = c_self + cond_vec

                for blk in self.blocks:
                    mods = blk["adaln"](c_self).reshape(B, -1, 6, dim)
                    shift_s, scale_s, gate_s = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
                    shift_c, scale_c, gate_c = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]
                    shift_f, scale_f, gate_f = mods[:, 2, 0], mods[:, 2, 1], mods[:, 2, 2]

                    h = self._modulate(blk["norm1"](tokens), shift_s, scale_s)
                    q = blk["self_attn"]["wq"](h)
                    k = blk["self_attn"]["wk"](h)
                    v = blk["self_attn"]["wv"](h)
                    attn_out = _F.scaled_dot_product_attention(q.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2),
                                                               k.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2),
                                                               v.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2)).transpose(1, 2).flatten(2)
                    tokens = tokens + gate_s.unsqueeze(1) * blk["self_attn"]["wo"](attn_out)

                    h = self._modulate(blk["norm2"](tokens), shift_c, scale_c)
                    kv = blk["cross_proj"](cross_ctx)
                    q = blk["cross_attn"]["wq"](h)
                    k = blk["cross_attn"]["wk"](kv)
                    v = blk["cross_attn"]["wv"](kv)
                    attn_out = _F.scaled_dot_product_attention(q.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2),
                                                               k.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2),
                                                               v.reshape(B, -1, c.num_heads, dim // c.num_heads).transpose(1, 2)).transpose(1, 2).flatten(2)
                    tokens = tokens + gate_c.unsqueeze(1) * blk["cross_attn"]["wo"](attn_out)

                    h = self._modulate(blk["norm3"](tokens), shift_f, scale_f)
                    ffn_out = blk["ffn"]["w2"](_F.silu(blk["ffn"]["w1"](h)) * blk["ffn"]["w3"](h))
                    tokens = tokens + gate_f.unsqueeze(1) * ffn_out

                tokens = self.final_norm(tokens)
                mods = self.final_adaln(c_self).reshape(B, 1, 6, dim)
                shift, scale = mods[:, 0, 0], mods[:, 0, 1]
                tokens = self._modulate(tokens, shift, scale)
                out = self.proj(tokens)
                Hn = Wn = int(math.sqrt(tokens.shape[1]))
                P = c.patch_size
                C = c.latent_channels
                out = out.reshape(B, Hn, Wn, P, P, C).permute(0, 5, 1, 3, 2, 4).reshape(B, C, Hn * P, Wn * P)
                return out

            def decode(self, latent: torch.Tensor) -> torch.Tensor:
                B, C, H, W = latent.shape
                P = c.patch_size
                Hn, Wn = H // P, W // P
                latent = latent[:, :, :Hn * P, :Wn * P]
                xp = latent.reshape(B, C, Hn, P, Wn, P).permute(0, 2, 4, 1, 3, 5).reshape(B, Hn * Wn, C * P * P)
                h = self.dec_proj(xp)
                h = self.final_norm(h)
                mods = self.final_adaln(torch.zeros((B, dim), device=x.device, dtype=x.dtype)).reshape(B, 1, 6, dim)
                shift, scale = mods[:, 0, 0], mods[:, 0, 1]
                h = self._modulate(h, shift, scale)
                out = self.dec_out(h)
                out = out.reshape(B, Hn, Wn, P, P, c.image_channels).permute(0, 5, 1, 3, 2, 4).reshape(B, c.image_channels, Hn * P, Wn * P)
                return out

        model = _TorchDiT(self)
        self._torch_model = model
        return model


# ----------------------------------------------------------------------
# Encoders / Decoders / Refiners
# ----------------------------------------------------------------------


class TextEncoder:
    def __init__(self, vocab_size: int = 4096, embed_dim: int = 128, out_dim: int = 256):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.out_dim = out_dim
        self.embed = np.random.uniform(-0.01, 0.01, (vocab_size, embed_dim)).astype(np.float32)
        self.proj = np.random.uniform(-0.01, 0.01, (embed_dim, out_dim)).astype(np.float32)

    def __call__(self, tokens: np.ndarray) -> np.ndarray:
        x = self.embed[np.asarray(tokens, dtype=np.int64)]
        return (x @ self.proj).mean(axis=0, keepdims=True)


class VisionEncoder:
    def __init__(self, in_channels: int = 3, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_channels, out_dim)).astype(np.float32)

    def __call__(self, image: np.ndarray) -> np.ndarray:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        pooled = x.mean(axis=(2, 3))
        return pooled @ self.proj


class IdentityEncoder:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class ObjectEncoder:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class SceneEncoder:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class SpatialEncoder:
    def __init__(self, out_dim: int = 128):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (2, out_dim)).astype(np.float32)

    def __call__(self, coords: np.ndarray) -> np.ndarray:
        x = np.asarray(coords, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class LatentCodec:
    def __init__(self, in_channels: int = 3, latent_channels: int = 4):
        self.in_channels = in_channels
        self.latent_channels = latent_channels
        self.enc_w = np.random.uniform(-0.01, 0.01, (latent_channels, in_channels, 3, 3)).astype(np.float32)
        self.dec_w = np.random.uniform(-0.01, 0.01, (in_channels, latent_channels, 3, 3)).astype(np.float32)

    def encode(self, image: np.ndarray) -> np.ndarray:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        B = x.shape[0]
        downsampled = x[:, :, ::2, ::2]
        out = np.zeros((B, self.latent_channels, downsampled.shape[2], downsampled.shape[3]), dtype=np.float32)
        for i in range(self.latent_channels):
            out[:, i] = np.tanh(downsampled.mean(axis=1) * float(self.enc_w[i].mean()) + np.sin(downsampled.mean(axis=1) * float(self.enc_w[i].mean())))
        return out

    def decode(self, latent: np.ndarray) -> np.ndarray:
        x = np.asarray(latent, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        B = x.shape[0]
        upsampled = np.repeat(x, 2, axis=2)
        upsampled = np.repeat(upsampled, 2, axis=3)
        out = np.zeros((B, self.in_channels, upsampled.shape[2], upsampled.shape[3]), dtype=np.float32)
        for i in range(self.in_channels):
            out[:, i] = np.tanh(upsampled.mean(axis=1) * float(self.dec_w[i].mean()) + np.cos(upsampled.mean(axis=1) * float(self.dec_w[i].mean())))
        return out


class DetailRefiner:
    def __init__(self, channels: int = 4):
        self.channels = channels
        self.w = np.random.uniform(-0.01, 0.01, (channels, 3, 3)).astype(np.float32)

    def __call__(self, latent: np.ndarray) -> np.ndarray:
        x = np.asarray(latent, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        refined = x + np.tanh(x) * 0.1
        return refined


class SuperResolutionModule:
    def __init__(self, scale: int = 2):
        self.scale = scale
        self.w = np.random.uniform(-0.01, 0.01, (3, 3, 3)).astype(np.float32)

    def __call__(self, image: np.ndarray) -> np.ndarray:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        up = np.repeat(x, self.scale, axis=2)
        up = np.repeat(up, self.scale, axis=3)
        sharpened = up + 0.1 * np.tanh(up)
        return sharpened.clip(0, 1)


class QualityController:
    def __init__(self):
        pass

    def assess(self, image: np.ndarray) -> Dict[str, float]:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        return {
            "sharpness": float(np.mean(np.abs(x[:, :, 1:] - x[:, :, :-1]))),
            "contrast": float(np.std(x)),
            "brightness": float(np.mean(x)),
        }


# ----------------------------------------------------------------------
# PyTorch bridge
# ----------------------------------------------------------------------


def to_torch(self):
    if not _HAVE_TORCH:
        raise RuntimeError("PyTorch not available")
    model = self._build_torch_model()
    state_dict = {}
    for name, arr in self.parameters().items():
        tensor = _torch.from_numpy(arr)
        state_dict[name] = tensor
    try:
        model.load_state_dict(state_dict, strict=False)
    except Exception:
        pass
    return model


# Monkey-patch onto ImageFoundationModel
ImageFoundationModel.to_torch = to_torch


# ----------------------------------------------------------------------
# Encoders / Decoders / Refiners
# ----------------------------------------------------------------------


class TextEncoder:
    def __init__(self, vocab_size=4096, embed_dim=128, out_dim=256):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.out_dim = out_dim
        self.embed = np.random.uniform(-0.01, 0.01, (vocab_size, embed_dim)).astype(np.float32)
        self.proj = np.random.uniform(-0.01, 0.01, (embed_dim, out_dim)).astype(np.float32)

    def __call__(self, tokens):
        x = self.embed[np.asarray(tokens, dtype=np.int64)]
        return (x @ self.proj).mean(axis=0, keepdims=True)


class VisionEncoder:
    def __init__(self, in_channels=3, out_dim=256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_channels, out_dim)).astype(np.float32)

    def __call__(self, image):
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        pooled = x.mean(axis=(2, 3))
        return pooled @ self.proj


class IdentityEncoder:
    def __init__(self, in_dim=128, out_dim=256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features):
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class ObjectEncoder:
    def __init__(self, in_dim=128, out_dim=256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features):
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class SceneEncoder:
    def __init__(self, in_dim=128, out_dim=256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features):
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class SpatialEncoder:
    def __init__(self, out_dim=128):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (2, out_dim)).astype(np.float32)

    def __call__(self, coords):
        x = np.asarray(coords, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class LatentCodec:
    def __init__(self, in_channels=3, latent_channels=4):
        self.in_channels = in_channels
        self.latent_channels = latent_channels
        self.enc_w = np.random.uniform(-0.01, 0.01, (latent_channels, in_channels, 3, 3)).astype(np.float32)
        self.dec_w = np.random.uniform(-0.01, 0.01, (in_channels, latent_channels, 3, 3)).astype(np.float32)

    def encode(self, image):
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        B = x.shape[0]
        downsampled = x[:, :, ::2, ::2]
        out = np.zeros((B, self.latent_channels, downsampled.shape[2], downsampled.shape[3]), dtype=np.float32)
        for i in range(self.latent_channels):
            out[:, i] = np.tanh(downsampled.mean(axis=1) * float(self.enc_w[i].mean()) + np.sin(downsampled.mean(axis=1) * float(self.enc_w[i].mean())))
        return out

    def decode(self, latent):
        x = np.asarray(latent, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        B = x.shape[0]
        upsampled = np.repeat(x, 2, axis=2)
        upsampled = np.repeat(upsampled, 2, axis=3)
        out = np.zeros((B, self.in_channels, upsampled.shape[2], upsampled.shape[3]), dtype=np.float32)
        for i in range(self.in_channels):
            out[:, i] = np.tanh(upsampled.mean(axis=1) * float(self.dec_w[i].mean()) + np.cos(upsampled.mean(axis=1) * float(self.dec_w[i].mean())))
        return out


class DetailRefiner:
    def __init__(self, channels=4):
        self.channels = channels
        self.w = np.random.uniform(-0.01, 0.01, (channels, 3, 3)).astype(np.float32)

    def __call__(self, latent):
        x = np.asarray(latent, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        refined = x + np.tanh(x) * 0.1
        return refined


class SuperResolutionModule:
    def __init__(self, scale=2):
        self.scale = scale
        self.w = np.random.uniform(-0.01, 0.01, (3, 3, 3)).astype(np.float32)

    def __call__(self, image):
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        up = np.repeat(x, self.scale, axis=2)
        up = np.repeat(up, self.scale, axis=3)
        sharpened = up + 0.1 * np.tanh(up)
        return sharpened.clip(0, 1)


class QualityController:
    def __init__(self):
        pass

    def assess(self, image):
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        return {
            "sharpness": float(np.mean(np.abs(x[:, :, 1:] - x[:, :, :-1]))),
            "contrast": float(np.std(x)),
            "brightness": float(np.mean(x)),
        }


__all__ = [
    "ImageConfig",
    "ImageFoundationModel",
    "TextEncoder",
    "VisionEncoder",
    "IdentityEncoder",
    "ObjectEncoder",
    "SceneEncoder",
    "SpatialEncoder",
    "LatentCodec",
    "DetailRefiner",
    "SuperResolutionModule",
    "QualityController",
]
