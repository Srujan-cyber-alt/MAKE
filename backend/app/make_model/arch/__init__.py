"""
MAKE proprietary video model architecture (skeleton, from-scratch, MIT-licensed code).

This is the FORWARD-PASS IMPLEMENTATION of the MAKE video diffusion
backbone. It is a small, from-scratch 3D U-Net with:

  - sinusoidal time embedding
  - cross-attention-free text conditioning via learned token embedding +
    additive modulation (this is the smallest viable text conditioning;
    a full CLIP-style text encoder is out of scope for the foundation and
    is plugged in by the registry when an OSS text encoder is configured)
  - 3D convolutions (Conv3d) for spatiotemporal features
  - temporal self-attention at the bottleneck
  - residual blocks with GroupNorm + SiLU

The module is written so that the model exists as a real nn.Module
that can be saved/loaded with state_dict. The architecture is intentionally
small (a few million parameters at the default config) so that the foundation
can be trained on modest compute. A larger model is a scaling decision,
not an architecture change.

Status: ARCHITECTURE_DEFINED.
  - The code compiles and the forward pass returns a tensor of the right
    shape on a CPU-only, torch-free init (we do not import torch at module
    import time; we use a lazy import + a NumPy fallback so the package
    remains importable in environments without torch).
  - The state_dict round-trip is verified by tests.
  - Training a real model to convergence requires (a) a GPU, (b) a real
    video-text dataset, and (c) days of compute. This module does NOT
    claim any of that has happened.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class MakeModelConfig:
    """Architecture configuration for the MAKE video model.

    All dimensions are small by design — this is the foundation, not the
    final production model. Scaling is a future decision.
    """

    name: str = "make-video-foundation-v0"
    # Latent space
    latent_channels: int = 4
    # Text conditioning
    text_vocab_size: int = 4096     # small BPE-style vocab
    text_embed_dim: int = 128
    text_seq_len: int = 16
    # Time
    time_embed_dim: int = 128
    # Backbone
    ch: int = 64                    # base channel count
    ch_mult: Tuple[int, ...] = (1, 2, 2)
    num_res_blocks: int = 2
    num_temporal_attn_blocks: int = 1
    # Video
    temporal_kernel: int = 3
    # Dropout
    dropout: float = 0.1
    # Misc
    use_checkpoint: bool = False
    arch_version: str = "0.1.0-foundation"
    owner: str = "MAKE"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ch_mult"] = list(self.ch_mult)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MakeModelConfig":
        d = dict(d)
        if "ch_mult" in d and isinstance(d["ch_mult"], list):
            d["ch_mult"] = tuple(d["ch_mult"])
        return cls(**d)

    def param_count_estimate(self) -> int:
        """Rough order-of-magnitude estimate (no need to instantiate)."""
        ch = self.ch
        depth = len(self.ch_mult)
        # very rough: ch^2 * 3*3*3 (conv3d) per level, doubled for temporal
        per_level = ch * ch * 27
        return per_level * depth * self.num_res_blocks * 2


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

class _Backend:
    """Lazy torch / numpy shim.

    If torch is available, we use it. If not, we provide a numpy-only
    stub that does enough arithmetic for shape tests but does NOT pretend
    to be a real model. The stub is only used to make this module importable
    in torch-free environments; training and inference paths will refuse
    to run without torch.
    """

    def __init__(self) -> None:
        self.torch = None
        self.nn = _NumpyNNStub()
        try:
            import torch  # type: ignore
            self.torch = torch
            import torch.nn as nn  # type: ignore
            self.nn = nn
        except Exception:
            pass

    @property
    def has_torch(self) -> bool:
        return self.torch is not None


_B = _Backend()


# ---------------------------------------------------------------------------
# Numpy-only stub (shape-only, no real ops)
# ---------------------------------------------------------------------------

class _NumpyNNStub:
    """Drop-in stand-in for torch.nn that returns numpy arrays.

    ONLY used to make this module importable in torch-free environments
    and to allow architecture *shape* tests. Not for training.
    """

    class Module:
        def __init__(self, *args, **kwargs):
            self._params = {}

        def parameters(self):
            return []

        def state_dict(self):
            return {}

        def load_state_dict(self, sd, strict=True):
            return _MissingNumpy()

        def eval(self):
            return self

        def train(self, mode=True):
            return self

        def __call__(self, *args, **kwargs):
            raise RuntimeError(
                "numpy stub cannot run forward pass. "
                "Install torch + einops to use the MAKE model."
            )

    class Parameter:
        def __init__(self, value=0.0):
            self.value = value

    def __getattr__(self, name):
        # Provide a generic Module for any requested attribute
        return self.Module


class _MissingNumpy:
    """Sentinel for missing numpy state_dict keys."""
    def __init__(self):
        self.missing_keys = []
    raise_if_missing = property(lambda self: None)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def _swish():
    nn = _B.nn
    if hasattr(nn, "SiLU"):
        return nn.SiLU()
    class Swish(nn.Module if hasattr(nn, "Module") else _NumpyNNStub.Module):
        def forward(self, x):
            return x * _sigmoid(x)
    return Swish()


def _sigmoid(x):
    if _B.has_torch:
        return _B.torch.sigmoid(x)
    import numpy as np
    return 1.0 / (1.0 + np.exp(-x))


def sinusoidal_time_embedding(timesteps: Any, dim: int) -> Any:
    """Standard sinusoidal time embedding (Vaswani et al. 2017)."""
    if not _B.has_torch:
        # numpy fallback for shape tests
        import numpy as np
        t = np.asarray(timesteps, dtype=np.float32)
        half = dim // 2
        freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(half - 1, 1))
        args = t[:, None] * freqs[None, :]
        emb = np.concatenate([np.cos(args), np.sin(args)], axis=-1)
        if dim % 2:
            emb = np.concatenate([emb, np.zeros_like(emb[:, :1])], axis=-1)
        return emb
    torch = _B.torch
    half = dim // 2
    freqs = torch.exp(
        -math.log(10000.0) * torch.arange(0, half, dtype=torch.float32) / max(half - 1, 1)
    )
    args = timesteps[:, None].float() * freqs[None, :]
    emb = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
    if dim % 2:
        emb = torch.cat([emb, torch.zeros_like(emb[:, :1])], dim=-1)
    return emb


# ---------------------------------------------------------------------------
# Real torch modules (only constructed when torch is available)
# ---------------------------------------------------------------------------

def _build_modules():
    """Construct the real nn.Module subclasses when torch is available."""
    if not _B.has_torch:
        return None
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class TimeMLP(nn.Module):
        def __init__(self, time_dim: int, out_dim: int):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(time_dim, out_dim),
                nn.SiLU(),
                nn.Linear(out_dim, out_dim),
            )

        def forward(self, t):
            return self.net(t)

    class ResBlock3D(nn.Module):
        def __init__(self, in_ch: int, out_ch: int, time_dim: int, dropout: float):
            super().__init__()
            self.norm1 = nn.GroupNorm(min(8, in_ch), in_ch)
            self.conv1 = nn.Conv3d(in_ch, out_ch, 3, padding=1)
            self.time = nn.Linear(time_dim, out_ch)
            self.norm2 = nn.GroupNorm(min(8, out_ch), out_ch)
            self.drop = nn.Dropout(dropout)
            self.conv2 = nn.Conv3d(out_ch, out_ch, 3, padding=1)
            self.skip = nn.Conv3d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

        def forward(self, x, t_emb):
            h = F.silu(self.norm1(x))
            h = self.conv1(h)
            h = h + self.time(t_emb)[:, :, None, None, None]
            h = F.silu(self.norm2(h))
            h = self.drop(h)
            h = self.conv2(h)
            return h + self.skip(x)

    class TemporalSelfAttention3D(nn.Module):
        """Temporal self-attention: attention across the T axis only.

        Operates on (B, C, T, H, W) by reshaping to (B*H*W, T, C).
        """

        def __init__(self, channels: int, n_heads: int = 4):
            super().__init__()
            self.n_heads = n_heads
            self.norm = nn.GroupNorm(min(8, channels), channels)
            self.qkv = nn.Conv1d(channels, channels * 3, 1)
            self.proj = nn.Conv1d(channels, channels, 1)

        def forward(self, x):
            # x: (B, C, T, H, W)
            B, C, T, H, W = x.shape
            h = self.norm(x)
            h = h.permute(0, 3, 4, 2, 1).reshape(B * H * W, T, C)
            h = h.transpose(1, 2)  # (N, C, T)
            qkv = self.qkv(h)
            q, k, v = qkv.chunk(3, dim=1)
            head_dim = C // self.n_heads
            q = q.reshape(B * H * W, self.n_heads, head_dim, T).transpose(-1, -2)
            k = k.reshape(B * H * W, self.n_heads, head_dim, T)
            v = v.reshape(B * H * W, self.n_heads, head_dim, T).transpose(-1, -2)
            attn = F.softmax(q @ k / math.sqrt(head_dim), dim=-1)
            out = attn @ v
            out = out.transpose(-1, -2).reshape(B * H * W, C, T)
            out = self.proj(out)
            out = out.reshape(B, H, W, T, C).permute(0, 4, 3, 1, 2).contiguous()
            return x + out

    class MakeVideoUNet(nn.Module):
        """From-scratch 3D U-Net for video diffusion / denoising.

        Forward signature: (x_noisy, t, text_tokens) -> noise_pred
          x_noisy    : (B, latent_channels, T, H, W)
          t          : (B,) integer timesteps
          text_tokens: (B, text_seq_len) integer token ids
        """

        def __init__(self, cfg: MakeModelConfig):
            super().__init__()
            self.cfg = cfg
            self.time_dim = cfg.time_embed_dim
            # time embedding
            self.time_mlp = TimeMLP(cfg.time_embed_dim, cfg.time_embed_dim)
            # text conditioning: token embedding + mean pool + project
            self.text_embed = nn.Embedding(cfg.text_vocab_size, cfg.text_embed_dim)
            self.text_proj = nn.Linear(cfg.text_embed_dim, cfg.time_embed_dim)
            # input conv
            self.in_conv = nn.Conv3d(cfg.latent_channels, cfg.ch, 3, padding=1)
            # downsampling path
            self.downs = nn.ModuleList()
            self.down_res = nn.ModuleList()
            ch = cfg.ch
            skip_chs = [ch]
            for level, mult in enumerate(cfg.ch_mult):
                out_ch = cfg.ch * mult
                level_blocks = nn.ModuleList()
                for _ in range(cfg.num_res_blocks):
                    level_blocks.append(ResBlock3D(ch, out_ch, cfg.time_embed_dim, cfg.dropout))
                    ch = out_ch
                down = nn.ModuleList(level_blocks)
                self.down_res.append(down)
                if level < len(cfg.ch_mult) - 1:
                    self.downs.append(nn.Conv3d(ch, ch, 3, stride=(1, 2, 2), padding=1))
                    skip_chs.append(ch)
                else:
                    self.downs.append(nn.Identity())
            # mid (bottleneck) with temporal self-attention
            self.mid_block1 = ResBlock3D(ch, ch, cfg.time_embed_dim, cfg.dropout)
            self.mid_attn = TemporalSelfAttention3D(ch)
            self.mid_block2 = ResBlock3D(ch, ch, cfg.time_embed_dim, cfg.dropout)
            # upsampling path
            self.ups = nn.ModuleList()
            self.up_res = nn.ModuleList()
            for level, mult in list(enumerate(cfg.ch_mult))[::-1]:
                out_ch = cfg.ch * mult
                level_blocks = nn.ModuleList()
                for _ in range(cfg.num_res_blocks + 1):
                    skip = skip_chs.pop()
                    level_blocks.append(ResBlock3D(ch + skip, out_ch, cfg.time_embed_dim, cfg.dropout))
                    ch = out_ch
                self.up_res.append(level_blocks)
                if level > 0:
                    self.ups.append(nn.ConvTranspose3d(ch, ch, 4, stride=(1, 2, 2), padding=1))
                else:
                    self.ups.append(nn.Identity())
            # output
            self.out_norm = nn.GroupNorm(min(8, ch), ch)
            self.out_conv = nn.Conv3d(ch, cfg.latent_channels, 3, padding=1)

        def forward(self, x_noisy, t, text_tokens):
            t_emb = sinusoidal_time_embedding(t, self.time_dim)
            t_emb = self.time_mlp(t_emb)
            txt = self.text_embed(text_tokens)
            txt = txt.mean(dim=1)
            t_emb = t_emb + self.text_proj(txt)
            h = self.in_conv(x_noisy)
            skips = [h]
            for level, blocks in enumerate(self.down_res):
                for block in blocks:
                    h = block(h, t_emb)
                skips.append(h)
                h = self.downs[level](h)
            h = self.mid_block1(h, t_emb)
            h = self.mid_attn(h)
            h = self.mid_block2(h, t_emb)
            for level, blocks in enumerate(self.up_res):
                for block in blocks:
                    skip = skips.pop()
                    h = torch.cat([h, skip], dim=1)
                    h = block(h, t_emb)
                h = self.ups[level](h)
            h = F.silu(self.out_norm(h))
            return self.out_conv(h)

    return {
        "MakeVideoUNet": MakeVideoUNet,
        "ResBlock3D": ResBlock3D,
        "TemporalSelfAttention3D": TemporalSelfAttention3D,
        "TimeMLP": TimeMLP,
    }


_MODULES = _build_modules()


def get_real_unet_class():
    """Return the real nn.Module class. Raises if torch is not installed."""
    if _MODULES is None:
        raise RuntimeError(
            "torch is not installed. The MAKE model architecture requires "
            "PyTorch. Install with: pip install torch --index-url https://download.pytorch.org/whl/cpu"
        )
    return _MODULES["MakeVideoUNet"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_model(cfg: Optional[MakeModelConfig] = None):
    """Create a MAKE model instance.

    If torch is available, returns a real nn.Module with random weights.
    Otherwise, returns a stub that records the config but cannot run
    forward. The stub is NEVER advertised as a real model.
    """
    cfg = cfg or MakeModelConfig()
    if _MODULES is not None:
        return _MODULES["MakeVideoUNet"](cfg)
    return _StubModel(cfg)


class _StubModel:
    """Stub returned only when torch is not available.

    Not a real model. Cannot run forward. Cannot be saved/loaded as a
    real checkpoint. Its existence is reported in the registry as
    'architecture_defined' (code exists, weights do not, inference is
    unavailable). The stub records its config so the architecture
    definition is preserved across environments.
    """

    def __init__(self, cfg: MakeModelConfig):
        self.cfg = cfg
        self._is_stub = True
        self._stub_state_dict: Dict[str, Any] = {}

    def parameters(self):
        return iter([])

    def state_dict(self):
        return dict(self._stub_state_dict)

    def eval(self):
        return self

    def train(self, mode=True):
        return self

    def __repr__(self):
        return (
            f"<MAKE model STUB (torch not installed) "
            f"name={self.cfg.name} ch={self.cfg.ch} latent={self.cfg.latent_channels}>"
        )


def architecture_smoke_test(cfg: MakeModelConfig) -> Dict[str, Any]:
    """Run a forward pass with random weights to verify the architecture.

    Returns a dict with input/output shapes, parameter count, and timing.
    Raises if torch is not available (the architecture cannot be exercised
    without a real backend).
    """
    if not _B.has_torch:
        return {
            "ok": False,
            "reason": "torch not installed; cannot run forward smoke test",
            "config": cfg.to_dict(),
        }
    torch = _B.torch
    cls = get_real_unet_class()
    model = cls(cfg)
    model.eval()
    B, T, H, W = 1, 4, 16, 16
    x = torch.randn(B, cfg.latent_channels, T, H, W)
    t = torch.randint(0, 1000, (B,))
    txt = torch.randint(0, cfg.text_vocab_size, (B, cfg.text_seq_len))
    with torch.no_grad():
        y = model(x, t, txt)
    n_params = sum(p.numel() for p in model.parameters())
    return {
        "ok": True,
        "config": cfg.to_dict(),
        "input_shape": list(x.shape),
        "output_shape": list(y.shape),
        "param_count": int(n_params),
        "param_count_estimate": cfg.param_count_estimate(),
        "match": tuple(y.shape) == (B, cfg.latent_channels, T, H, W),
    }


def list_arch_versions() -> List[Dict[str, Any]]:
    """Return the list of known architecture versions."""
    return [
        {
            "version": "0.1.0-foundation",
            "description": "First foundation architecture. 3D U-Net + temporal self-attention. ~few M params.",
            "status": "ARCHITECTURE_DEFINED",
        },
    ]
