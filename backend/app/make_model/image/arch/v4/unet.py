"""
v4 multi-scale UNet for the MAKE image subsystem.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Tuple, List, Optional

import numpy as np

from app.make_model.image.arch.v2.conditioning import (
    ConditionVector, DEFAULT_CONDITION_DIM,
)
from app.make_model.image.arch.unet import (
    _im2col, _col2im, conv2d_forward, group_norm, NumpyUNetConfig,
)


def sinusoidal_timestep_embedding(timesteps: np.ndarray, dim: int = 128) -> np.ndarray:
    half = dim // 2
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / half)
    args = timesteps.astype(np.float32)[:, None] * freqs[None, :]
    emb = np.concatenate([np.cos(args), np.sin(args)], axis=1)
    if dim % 2 == 1:
        emb = np.pad(emb, ((0, 0), (0, 1)))
    return emb


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_max = np.max(x, axis=axis, keepdims=True)
    e = np.exp(x - x_max)
    return e / np.sum(e, axis=axis, keepdims=True)


def multi_head_cross_attention(
    q_in: np.ndarray, kv_in: np.ndarray,
    w_q: np.ndarray, w_k: np.ndarray, w_v: np.ndarray, w_o: np.ndarray,
    b_q: np.ndarray, b_k: np.ndarray, b_v: np.ndarray, b_o: np.ndarray,
    num_heads: int = 4,
) -> np.ndarray:
    B, Tq, C = q_in.shape
    Tk = kv_in.shape[1]
    head_dim = max(1, C // num_heads)
    qp = q_in @ w_q.T + b_q.reshape(1, 1, -1)
    kp = kv_in @ w_k.T + b_k.reshape(1, 1, -1)
    vp = kv_in @ w_v.T + b_v.reshape(1, 1, -1)
    q = qp.reshape(B, Tq, num_heads, head_dim).transpose(0, 2, 1, 3)
    k = kp.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
    v = vp.reshape(B, Tk, num_heads, head_dim).transpose(0, 2, 1, 3)
    scale = 1.0 / math.sqrt(head_dim)
    scores = np.einsum("bhqd,bhkd->bhqk", q, k) * scale
    attn = _softmax(scores, axis=-1)
    out = np.einsum("bhqk,bhkd->bhqd", attn, v)
    out = out.transpose(0, 2, 1, 3).reshape(B, Tq, C)
    out = out @ w_o.T + b_o.reshape(1, 1, -1)
    return out


def adagn(x: np.ndarray, scale: np.ndarray, shift: np.ndarray,
          groups: int = 1, eps: float = 1e-5) -> np.ndarray:
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


class PreNormResBlock:
    def __init__(self, in_ch: int, out_ch: int, tcc_dim: int,
                 rng: np.random.Generator, groups: int = 4):
        self.in_ch, self.out_ch = in_ch, out_ch
        k = 3
        scale = (1.0 / max(1.0, in_ch * k * k)) ** 0.5
        self.w1 = (rng.standard_normal((out_ch, in_ch, k, k)) * scale).astype(np.float32)
        self.b1 = np.zeros((out_ch,), dtype=np.float32)
        self.w2 = (rng.standard_normal((out_ch, out_ch, k, k)) * (1.0 / max(1.0, out_ch * k * k)) ** 0.5).astype(np.float32)
        self.b2 = np.zeros((out_ch,), dtype=np.float32)
        self.gn1_g = np.ones((in_ch,), dtype=np.float32)
        self.gn1_b = np.zeros((in_ch,), dtype=np.float32)
        self.gn2_g = np.ones((out_ch,), dtype=np.float32)
        self.gn2_b = np.zeros((out_ch,), dtype=np.float32)
        self.mod = (rng.standard_normal((out_ch * 4, tcc_dim)) * (1.0 / tcc_dim ** 0.5)).astype(np.float32)
        self.groups = min(groups, max(1, out_ch))
        if in_ch != out_ch:
            self.skip = (rng.standard_normal((out_ch, in_ch, 1, 1)) * scale).astype(np.float32)
        else:
            self.skip = None

    def forward(self, x: np.ndarray, tcc: np.ndarray) -> np.ndarray:
        mod = tcc @ self.mod.T
        out_ch = self.out_ch
        gamma1 = mod[:, :out_ch]; beta1 = mod[:, out_ch:2*out_ch]
        h = group_norm(x, self.gn1_g, self.gn1_b, groups=min(self.groups, max(1, self.in_ch)))
        h = np.maximum(0.0, h)
        h = conv2d_forward(h, self.w1, self.b1, pad=1)
        h = group_norm(h, self.gn2_g, self.gn2_b, groups=self.groups)
        h = adagn(h, gamma1, beta1, groups=self.groups)
        h = np.maximum(0.0, h)
        h = conv2d_forward(h, self.w2, self.b2, pad=1)
        if self.skip is not None:
            x = conv2d_forward(x, self.skip, np.zeros(self.out_ch, dtype=np.float32))
        return x + h

    def parameters(self) -> Dict[str, np.ndarray]:
        return {
            "w1": self.w1, "b1": self.b1,
            "w2": self.w2, "b2": self.b2,
            "gn1_g": self.gn1_g, "gn1_b": self.gn1_b,
            "gn2_g": self.gn2_g, "gn2_b": self.gn2_b,
            "mod": self.mod,
            **({"skip": self.skip} if self.skip is not None else {}),
        }


class CrossAttentionBlock:
    def __init__(self, channels: int, cond_dim: int, num_heads: int = 4,
                 rng: np.random.Generator = None, mlp_ratio: float = 2.0):
        self.channels = channels
        self.num_heads = num_heads
        self.head_dim = max(1, channels // num_heads)
        scale = (1.0 / channels) ** 0.5
        self.ln_g = np.ones((channels,), dtype=np.float32)
        self.ln_b = np.zeros((channels,), dtype=np.float32)
        self.w_q = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_q = np.zeros((channels,), dtype=np.float32)
        self.w_k = (rng.standard_normal((channels, cond_dim)) * scale).astype(np.float32)
        self.b_k = np.zeros((channels,), dtype=np.float32)
        self.w_v = (rng.standard_normal((channels, cond_dim)) * scale).astype(np.float32)
        self.b_v = np.zeros((channels,), dtype=np.float32)
        self.w_o = (rng.standard_normal((channels, channels)) * scale).astype(np.float32)
        self.b_o = np.zeros((channels,), dtype=np.float32)
        mlp_hidden = max(channels, int(channels * mlp_ratio))
        self.w_mlp1 = (rng.standard_normal((mlp_hidden, channels)) * scale).astype(np.float32)
        self.b_mlp1 = np.zeros((mlp_hidden,), dtype=np.float32)
        self.w_mlp2 = (rng.standard_normal((channels, mlp_hidden)) * scale).astype(np.float32)
        self.b_mlp2 = np.zeros((channels,), dtype=np.float32)

    def forward(self, x: np.ndarray, cond: np.ndarray) -> np.ndarray:
        B, C, H, W = x.shape
        residual = x
        xn = group_norm(x, self.ln_g, self.ln_b, groups=1)
        xn = xn.reshape(B, C, H * W).transpose(0, 2, 1)
        out = multi_head_cross_attention(
            xn, cond, self.w_q, self.w_k, self.w_v, self.w_o,
            self.b_q, self.b_k, self.b_v, self.b_o,
            num_heads=self.num_heads,
        )
        out = out.transpose(0, 2, 1).reshape(B, C, H, W)
        x = residual + out
        residual = x
        xn = group_norm(x, self.ln_g, self.ln_b, groups=1)
        xn = xn.reshape(B, C, H * W).transpose(0, 2, 1)
        h = np.maximum(0.0, xn @ self.w_mlp1.T + self.b_mlp1)
        h = h @ self.w_mlp2.T + self.b_mlp2
        h = h.transpose(0, 2, 1).reshape(B, C, H, W)
        return residual + h

    def parameters(self) -> Dict[str, np.ndarray]:
        return {
            "ln_g": self.ln_g, "ln_b": self.ln_b,
            "w_q": self.w_q, "b_q": self.b_q,
            "w_k": self.w_k, "b_k": self.b_k,
            "w_v": self.w_v, "b_v": self.b_v,
            "w_o": self.w_o, "b_o": self.b_o,
            "w_mlp1": self.w_mlp1, "b_mlp1": self.b_mlp1,
            "w_mlp2": self.w_mlp2, "b_mlp2": self.b_mlp2,
        }


@dataclass
class NumpyUNetV4Config:
    image_size: int = 32
    in_channels: int = 3
    base_channels: int = 32
    channel_mults: Tuple[int, ...] = (1, 2, 4)
    num_res_blocks: int = 3
    condition_dim: int = DEFAULT_CONDITION_DIM
    time_dim: int = 128
    identity_dim: int = 16
    num_timesteps: int = 200
    arch_version: str = "make-image-cpu-unet-v4"
    attention_resolutions: Tuple[int, ...] = (8, 16)
    num_attention_heads: int = 4
    use_identity_bypass: bool = True
    use_detail_head: bool = True
    use_sinusoidal_time: bool = True
    notes: str = "v4: sinusoidal time emb + multi-scale cross-attn + deeper resblocks"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        d["attention_resolutions"] = list(self.attention_resolutions)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NumpyUNetV4Config":
        d = dict(d)
        d["channel_mults"] = tuple(int(x) for x in d.get("channel_mults", (1, 2, 4)))
        d["attention_resolutions"] = tuple(int(x) for x in d.get("attention_resolutions", (8, 16)))
        return cls(**d)


class NumpyUNetV4:
    def __init__(self, cfg: NumpyUNetV4Config, seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        td, cd = cfg.time_dim, cfg.condition_dim
        in_dim = td + cd

        self.use_sinusoidal = cfg.use_sinusoidal_time
        if self.use_sinusoidal:
            self.time_mlp_w1 = (self.rng.standard_normal((td * 2, td)) * (1.0 / td ** 0.5)).astype(np.float32)
            self.time_mlp_b1 = np.zeros((td * 2,), dtype=np.float32)
            self.time_mlp_w2 = (self.rng.standard_normal((td, td * 2)) * (1.0 / (td * 2) ** 0.5)).astype(np.float32)
            self.time_mlp_b2 = np.zeros((td,), dtype=np.float32)
            self._time_cache: Dict[int, np.ndarray] = {}

        self.cond_mlp_w1 = (self.rng.standard_normal((cd * 2, cd)) * (1.0 / cd ** 0.5)).astype(np.float32)
        self.cond_mlp_b1 = np.zeros((cd * 2,), dtype=np.float32)
        self.cond_mlp_w2 = (self.rng.standard_normal((cd, cd * 2)) * (1.0 / (cd * 2) ** 0.5)).astype(np.float32)
        self.cond_mlp_b2 = np.zeros((cd,), dtype=np.float32)

        self.tc_w1 = (self.rng.standard_normal((in_dim * 2, in_dim)) * (1.0 / in_dim ** 0.5)).astype(np.float32)
        self.tc_b1 = np.zeros((in_dim * 2,), dtype=np.float32)
        self.tc_w2 = (self.rng.standard_normal((in_dim, in_dim * 2)) * (1.0 / (in_dim * 2) ** 0.5)).astype(np.float32)
        self.tc_b2 = np.zeros((in_dim,), dtype=np.float32)

        k = 3
        ch = cfg.base_channels
        self.stem_w = (self.rng.standard_normal((ch, cfg.in_channels, k, k)) * (1.0 / (cfg.in_channels * k * k) ** 0.5)).astype(np.float32)
        self.stem_b = np.zeros((ch,), dtype=np.float32)

        self.enc_levels: List[Dict[str, Any]] = []
        cur_ch = ch
        resolution = cfg.image_size
        for level, mult in enumerate(cfg.channel_mults):
            out_ch = ch * mult
            blocks = [PreNormResBlock(cur_ch if i == 0 else out_ch, out_ch, in_dim, self.rng, groups=4)
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

        self.mid1 = PreNormResBlock(cur_ch, cur_ch, in_dim, self.rng, groups=4)
        self.mid2 = PreNormResBlock(cur_ch, cur_ch, in_dim, self.rng, groups=4)

        if cfg.use_identity_bypass:
            self.id_w = (self.rng.standard_normal((cur_ch, cfg.identity_dim)) * (1.0 / cfg.identity_dim ** 0.5)).astype(np.float32)
            self.id_b = np.zeros((cur_ch,), dtype=np.float32)
        else:
            self.id_w = None
            self.id_b = None

        self.dec_levels: List[Dict[str, Any]] = []
        for level, mult in enumerate(reversed(cfg.channel_mults)):
            out_ch = ch * mult
            skip_ch = ch * mult
            in_ch = cur_ch + skip_ch
            blocks = [PreNormResBlock(in_ch if i == 0 else out_ch, out_ch, in_dim, self.rng, groups=4)
                      for i in range(cfg.num_res_blocks)]
            self.dec_levels.append({
                "blocks": blocks,
                "out_ch": out_ch,
                "in_ch_first": in_ch,
                "level": level,
            })
            cur_ch = out_ch

        self.out_gn_g = np.ones((cur_ch,), dtype=np.float32)
        self.out_gn_b = np.zeros((cur_ch,), dtype=np.float32)
        self.out_w = (self.rng.standard_normal((cfg.in_channels, cur_ch, k, k)) * (1.0 / (cur_ch * k * k) ** 0.5)).astype(np.float32)
        self.out_b = np.zeros((cfg.in_channels,), dtype=np.float32)

        if cfg.use_detail_head:
            scale_det = (1.0 / max(1.0, cur_ch * k * k)) ** 0.5
            self.det_w = (self.rng.standard_normal((cur_ch, cur_ch, k, k)) * scale_det).astype(np.float32)
            self.det_b = np.zeros((cur_ch,), dtype=np.float32)
            self.det_out = (self.rng.standard_normal((cfg.in_channels, cur_ch, 1, 1)) * (1.0 / cur_ch)).astype(np.float32)
        else:
            self.det_w = None

    def _time_emb(self, t: np.ndarray) -> np.ndarray:
        if self.use_sinusoidal:
            out = []
            for ti in t:
                ti_int = int(ti)
                if ti_int not in self._time_cache:
                    emb = sinusoidal_timestep_embedding(np.array([ti_int], dtype=np.int64), self.cfg.time_dim)
                    self._time_cache[ti_int] = emb[0]
                out.append(self._time_cache[ti_int])
            t_emb = np.stack(out, axis=0)
            h = np.maximum(0.0, t_emb @ self.time_mlp_w1.T + self.time_mlp_b1)
            h = h @ self.time_mlp_w2.T + self.time_mlp_b2
            return h
        else:
            t_float = t.astype(np.float32)[:, None] / max(self.cfg.num_timesteps, 1)
            return np.concatenate([t_float, np.sin(t_float * math.pi)], axis=1)

    def _cond_emb(self, cond_vec: np.ndarray) -> np.ndarray:
        h = np.maximum(0.0, cond_vec @ self.cond_mlp_w1.T + self.cond_mlp_b1)
        h = h @ self.cond_mlp_w2.T + self.cond_mlp_b2
        return h

    def _fuse_tc(self, t_emb: np.ndarray, c_emb: np.ndarray) -> np.ndarray:
        tc = np.concatenate([t_emb, c_emb], axis=1)
        h = np.maximum(0.0, tc @ self.tc_w1.T + self.tc_b1)
        h = h @ self.tc_w2.T + self.tc_b2
        return h

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

        t_emb = self._time_emb(t)
        c_emb = self._cond_emb(cond_vec)
        tcc = self._fuse_tc(t_emb, c_emb)

        h = conv2d_forward(x, self.stem_w, self.stem_b, pad=1)
        skips = []
        for lvl in self.enc_levels:
            for rb in lvl["blocks"]:
                h = rb.forward(h, tcc)
            skips.append(h)
            if lvl["downsample"]:
                h = h.reshape(h.shape[0], h.shape[1], h.shape[2] // 2, 2, h.shape[3] // 2, 2).mean(axis=(3, 5))

        h = self.mid1.forward(h, tcc)
        h = self.mid2.forward(h, tcc)

        if self.id_w is not None and identity_vec is not None:
            idb = identity_vec @ self.id_w.T + self.id_b
            b, c = idb.shape
            bcast = idb.reshape(b, c, 1, 1) + np.zeros((1, 1, h.shape[2], h.shape[3]), dtype=np.float32)
            h = h + bcast

        for lvl in self.dec_levels:
            skip_h = skips.pop()
            if h.shape[2] != skip_h.shape[2] or h.shape[3] != skip_h.shape[3]:
                h = h.repeat(2, axis=2).repeat(2, axis=3)
            h = np.concatenate([h, skip_h], axis=1)
            for rb in lvl["blocks"]:
                h = rb.forward(h, tcc)

        h = group_norm(h, self.out_gn_g, self.out_gn_b, groups=4)
        h = np.maximum(0.0, h)
        out = conv2d_forward(h, self.out_w, self.out_b, pad=1)

        if self.det_w is not None:
            det = conv2d_forward(h, self.det_w, self.det_b, pad=1)
            det = np.maximum(0.0, det)
            det_out = conv2d_forward(det, self.det_out, np.zeros(cfg.in_channels, dtype=np.float32), pad=0)
            out = out + det_out

        return out

    def parameters(self) -> Dict[str, np.ndarray]:
        params: Dict[str, np.ndarray] = {}
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            val = getattr(self, attr)
            if isinstance(val, np.ndarray):
                params[attr] = val
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, np.ndarray):
                        params[f"{attr}.{k}"] = v
                    elif isinstance(v, list):
                        for i, item in enumerate(v):
                            if isinstance(item, np.ndarray):
                                params[f"{attr}.{k}.{i}"] = item
                            elif isinstance(item, dict):
                                for k2, v2 in item.items():
                                    if isinstance(v2, np.ndarray):
                                        params[f"{attr}.{k}.{i}.{k2}"] = v2
                                    elif isinstance(v2, list):
                                        for j, sub in enumerate(v2):
                                            if isinstance(sub, np.ndarray):
                                                params[f"{attr}.{k}.{i}.{k2}.{j}"] = sub
                                            elif hasattr(sub, "parameters"):
                                                for pk, pv in sub.parameters().items():
                                                    params[f"{attr}.{k}.{i}.{k2}.{j}.{pk}"] = pv
                                    elif hasattr(v2, "parameters"):
                                        for pk, pv in v2.parameters().items():
                                            params[f"{attr}.{k}.{i}.{k2}.{pk}"] = pv
                    elif hasattr(v, "parameters"):
                        for pk, pv in v.parameters().items():
                            params[f"{attr}.{k}.{pk}"] = pv
            elif isinstance(val, list):
                for i, v in enumerate(val):
                    if isinstance(v, np.ndarray):
                        params[f"{attr}.{i}"] = v
                    elif isinstance(v, dict):
                        for k2, v2 in v.items():
                            if isinstance(v2, np.ndarray):
                                params[f"{attr}.{i}.{k2}"] = v2
                            elif isinstance(v2, list):
                                for j, sub in enumerate(v2):
                                    if isinstance(sub, np.ndarray):
                                        params[f"{attr}.{i}.{k2}.{j}"] = sub
                                    elif hasattr(sub, "parameters"):
                                        for pk, pv in sub.parameters().items():
                                            params[f"{attr}.{i}.{k2}.{j}.{pk}"] = pv
                            elif hasattr(v2, "parameters"):
                                for pk, pv in v2.parameters().items():
                                    params[f"{attr}.{i}.{k2}.{pk}"] = pv
                    elif hasattr(v, "parameters"):
                        for pk, pv in v.parameters().items():
                            params[f"{attr}.{i}.{pk}"] = pv
            elif hasattr(val, "parameters"):
                for k, v in val.parameters().items():
                    params[f"{attr}.{k}"] = v
        return params

    def state_dict(self) -> Dict[str, np.ndarray]:
        return self.parameters()

    def load_state_dict(self, state: Dict[str, np.ndarray], strict: bool = True) -> None:
        for k, v in state.items():
            if "." in k:
                parts = k.split(".")
                obj = self
                for p in parts[:-1]:
                    if p.isdigit():
                        obj = obj[int(p)]
                    else:
                        obj = getattr(obj, p)
                setattr(obj, parts[-1], v)
            else:
                if hasattr(self, k):
                    setattr(self, k, v)
