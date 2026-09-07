"""
MAKE V4 Image Model Architecture - Simplified 2D U-Net.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class ImageModelConfig:
    name: str = "make-image-v4"
    latent_channels: int = 4
    text_vocab_size: int = 4096
    text_embed_dim: int = 256
    text_seq_len: int = 77
    time_embed_dim: int = 256
    ch: int = 64
    ch_mult: Tuple[int, ...] = (1, 2, 4)
    num_res_blocks: int = 2
    dropout: float = 0.0
    arch_version: str = "4.0.0"
    resolution: int = 256
    out_channels: int = 4

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ch_mult"] = list(self.ch_mult)
        return d


def timestep_embedding(timesteps: torch.Tensor, dim: int) -> torch.Tensor:
    half = dim // 2
    freqs = torch.exp(-math.log(10000.0) * torch.arange(0, half, dtype=torch.float32) / half)
    args = timesteps[:, None].float() * freqs[None]
    emb = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
    if dim % 2:
        emb = torch.cat([emb, torch.zeros_like(emb[:, :1])], dim=-1)
    return emb


class ResBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, time_dim: int):
        super().__init__()
        self.norm1 = nn.GroupNorm(32, in_ch)
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.time = nn.Linear(time_dim, out_ch)
        self.norm2 = nn.GroupNorm(32, out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.skip = nn.Conv2d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        h = F.silu(self.norm1(x))
        h = self.conv1(h)
        h = h + self.time(t)[:, :, None, None]
        h = F.silu(self.norm2(h))
        h = self.conv2(h)
        return h + self.skip(x)


class MakeImageUNet(nn.Module):
    def __init__(self, cfg: ImageModelConfig):
        super().__init__()
        self.cfg = cfg
        self.ch = cfg.ch
        self.time_dim = cfg.time_embed_dim

        self.time_mlp = nn.Sequential(
            nn.Linear(cfg.time_embed_dim, cfg.time_embed_dim),
            nn.SiLU(),
            nn.Linear(cfg.time_embed_dim, cfg.time_embed_dim),
        )
        self.text_embed = nn.Embedding(cfg.text_vocab_size, cfg.text_embed_dim)
        self.text_proj = nn.Linear(cfg.text_embed_dim, cfg.time_embed_dim)

        self.in_conv = nn.Conv2d(cfg.latent_channels, cfg.ch, 3, padding=1)

        ch = cfg.ch
        self.down_blocks = nn.ModuleList()
        self.down_channels = []

        for mult in cfg.ch_mult:
            out_ch = cfg.ch * mult
            self.down_blocks.append(ResBlock(ch, out_ch, cfg.time_embed_dim))
            self.down_channels.append(out_ch)
            ch = out_ch

        self.mid = ResBlock(ch, ch, cfg.time_embed_dim)

        self.up_blocks = nn.ModuleList()
        for mult in cfg.ch_mult[::-1]:
            out_ch = cfg.ch * mult
            self.up_blocks.append(ResBlock(ch + out_ch, out_ch, cfg.time_embed_dim))
            ch = out_ch

        self.out = nn.Sequential(
            nn.GroupNorm(32, ch),
            nn.SiLU(),
            nn.Conv2d(ch, cfg.out_channels, 3, padding=1),
        )

    def forward(self, x: torch.Tensor, t: torch.Tensor, txt: torch.Tensor) -> torch.Tensor:
        t_emb = timestep_embedding(t, self.time_dim)
        t_emb = self.time_mlp(t_emb)
        txt_emb = self.text_embed(txt).mean(dim=1)
        t_emb = t_emb + self.text_proj(txt_emb)

        h = self.in_conv(x)
        skips = [h]

        for block in self.down_blocks:
            h = block(h, t_emb)
            skips.append(h)

        h = self.mid(h, t_emb)

        for block in self.up_blocks:
            skip = skips.pop()
            h = torch.cat([h, skip], dim=1)
            h = block(h, t_emb)

        return self.out(h)


def architecture_smoke_test(cfg: ImageModelConfig) -> Dict[str, Any]:
    model = MakeImageUNet(cfg)
    model.eval()
    
    x = torch.randn(1, cfg.latent_channels, 32, 32)
    t = torch.randint(0, 1000, (1,))
    txt = torch.randint(0, cfg.text_vocab_size, (1, cfg.text_seq_len))
    
    with torch.no_grad():
        y = model(x, t, txt)
    
    n_params = sum(p.numel() for p in model.parameters())
    
    return {
        "ok": True,
        "input_shape": list(x.shape),
        "output_shape": list(y.shape),
        "param_count": n_params,
        "match": y.shape == x.shape,
    }


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.9999):
        self.model = model
        self.decay = decay
        self.shadow = {n: p.data.clone() for n, p in model.named_parameters() if p.requires_grad}

    def update(self):
        for n, p in self.model.named_parameters():
            if p.requires_grad:
                self.shadow[n] = self.decay * self.shadow[n] + (1 - self.decay) * p.data


def list_arch_versions() -> List[Dict[str, Any]]:
    return [{"version": "4.0.0", "description": "V4 Image Foundation"}]
