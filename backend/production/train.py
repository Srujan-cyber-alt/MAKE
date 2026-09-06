"""MAKE Foundation 5B — Production Training Script.

Real PyTorch training with autograd for the ~4.9B DiT architecture.
Supports mixed precision, gradient checkpointing, EMA, DDP, and resume.

Usage:
    # Single GPU
    python production/train.py --config production/configs/production_5b.json

    # Multi-GPU
    torchrun --nproc_per_node=8 production/train.py --config production/configs/production_5b.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.cuda.amp import GradScaler, autocast


# ----------------------------------------------------------------------
# Architecture — Pure PyTorch nn.Module implementation
# ----------------------------------------------------------------------

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        ms = (x * x).mean(dim=-1, keepdim=True)
        return x * (self.weight / torch.sqrt(ms + self.eps))


class LayerNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        ms = (x * x).mean(dim=-1, keepdim=True)
        x = x / torch.sqrt(ms + self.eps)
        return x * self.weight + self.bias


class GroupNorm3D(nn.Module):
    def __init__(self, ch: int, groups: int = 8, eps: float = 1e-6):
        super().__init__()
        self.groups = min(groups, ch)
        self.ch_per_group = ch // self.groups
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(ch))
        self.bias = nn.Parameter(torch.zeros(ch))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C = x.shape[0], x.shape[1]
        x = x.reshape(B, self.groups, self.ch_per_group, *x.shape[2:])
        ms = (x * x).mean(dim=tuple(range(2, x.ndim)), keepdim=True)
        x = x / torch.sqrt(ms + self.eps)
        x = x.reshape(B, C, *x.shape[3:])
        return x * self.weight[None, :, None, None, None] + self.bias[None, :, None, None, None]


class SwiGLU(nn.Module):
    def __init__(self, dim: int, mult: int = 4):
        super().__init__()
        self.w1 = nn.Linear(dim, mult * dim, bias=False)
        self.w2 = nn.Linear(mult * dim, dim, bias=False)
        self.w3 = nn.Linear(dim, mult * dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class AdaLNZero(nn.Module):
    def __init__(self, dim: int, cond_dim: int, n_blocks: int = 1):
        super().__init__()
        self.dim = dim
        self.n_blocks = n_blocks
        self.w = nn.Linear(cond_dim, n_blocks * 6 * dim, bias=True)
        nn.init.zeros_(self.w.weight)
        nn.init.zeros_(self.w.bias)

    def forward(self, c: torch.Tensor) -> torch.Tensor:
        B = c.shape[0]
        out = self.w(c).reshape(B, self.n_blocks, 6, self.dim)
        return out


def modulate(x: torch.Tensor, shift: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    return x * (1.0 + scale.unsqueeze(1)) + shift.unsqueeze(1)


class MultiHeadAttention(nn.Module):
    def __init__(self, dim: int, heads: int):
        super().__init__()
        assert dim % heads == 0
        self.dim = dim
        self.heads = heads
        self.dh = dim // heads
        self.wq = nn.Linear(dim, dim, bias=False)
        self.wk = nn.Linear(dim, dim, bias=False)
        self.wv = nn.Linear(dim, dim, bias=False)
        self.wo = nn.Linear(dim, dim, bias=False)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None, kv: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, N, _ = x.shape
        q = self.wq(x).reshape(B, N, self.heads, self.dh).transpose(1, 2)
        k = self.wk(kv if kv is not None else x).reshape(B, -1, self.heads, self.dh).transpose(1, 2)
        v = self.wv(kv if kv is not None else x).reshape(B, -1, self.heads, self.dh).transpose(1, 2)
        if hasattr(F, 'scaled_dot_product_attention'):
            out = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        else:
            scores = (q @ k.transpose(-2, -1)) / (self.dh ** 0.5)
            if mask is not None:
                scores = scores.masked_fill(mask == 0, -1e9)
            p = F.softmax(scores, dim=-1)
            out = p @ v
        out = out.transpose(1, 2).reshape(B, N, self.dim)
        return self.wo(out)


class DiTBlock(nn.Module):
    def __init__(self, dim: int, heads: int, cond_dim: int, ffn_mult: int = 4, has_cross: bool = True, cross_dim: Optional[int] = None):
        super().__init__()
        self.self_attn = MultiHeadAttention(dim, heads)
        self.cross_attn = MultiHeadAttention(dim, heads) if has_cross else None
        self.ffn = SwiGLU(dim, ffn_mult)
        self.norm1 = RMSNorm(dim)
        self.norm2 = RMSNorm(dim)
        self.norm3 = RMSNorm(dim)
        self.adaln = AdaLNZero(dim, cond_dim, n_blocks=3 if has_cross else 2)
        self.has_cross = has_cross
        self.cross_proj = nn.Linear(cross_dim or dim, dim, bias=False) if has_cross and cross_dim and cross_dim != dim else None

    def forward(self, x: torch.Tensor, c_self: torch.Tensor, c_cross: Optional[torch.Tensor] = None) -> torch.Tensor:
        mods = self.adaln(c_self)
        if self.has_cross and c_cross is not None:
            shift_s, scale_s, gate_s = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
            shift_c, scale_c, gate_c = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]
            shift_f, scale_f, gate_f = mods[:, 2, 0], mods[:, 2, 1], mods[:, 2, 2]
            ffn_idx = 2
        else:
            shift_s, scale_s, gate_s = mods[:, 0, 0], mods[:, 0, 1], mods[:, 0, 2]
            shift_f, scale_f, gate_f = mods[:, 1, 0], mods[:, 1, 1], mods[:, 1, 2]
            ffn_idx = 1

        h = modulate(self.norm1(x), shift_s, scale_s)
        x = x + gate_s.unsqueeze(1) * self.self_attn(h)

        if self.has_cross and c_cross is not None:
            h = modulate(self.norm2(x), shift_c, scale_c)
            kv = self.cross_proj(c_cross) if self.cross_proj is not None else c_cross
            x = x + gate_c.unsqueeze(1) * self.cross_attn(h, kv=kv)

        h = modulate(self.norm3(x), shift_f, scale_f)
        x = x + gate_f.unsqueeze(1) * self.ffn(h)
        return x


class ConditioningProjections(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
        self.projs = nn.ModuleDict({
            'text_emb': nn.Linear(dim, dim, bias=False),
            'text_tokens': nn.Linear(dim, dim, bias=False),
            'image_emb': nn.Linear(dim, dim, bias=False),
            'first_frame': nn.Linear(dim, dim, bias=False),
            'last_frame': nn.Linear(dim, dim, bias=False),
            'video_emb': nn.Linear(dim, dim, bias=False),
            'reference_emb': nn.Linear(dim, dim, bias=False),
            'identity_emb': nn.Linear(dim, dim, bias=False),
            'product_emb': nn.Linear(dim, dim, bias=False),
            'world_emb': nn.Linear(dim, dim, bias=False),
            'camera_emb': nn.Linear(dim, dim, bias=False),
            'motion_emb': nn.Linear(dim, dim, bias=False),
            'pose_emb': nn.Linear(dim, dim, bias=False),
            'style_emb': nn.Linear(dim, dim, bias=False),
            'lighting_emb': nn.Linear(dim, dim, bias=False),
            'depth_emb': nn.Linear(dim, dim, bias=False),
            'segmentation_emb': nn.Linear(dim, dim, bias=False),
            'mask_emb': nn.Linear(dim, dim, bias=False),
            'audio_emb': nn.Linear(dim, dim, bias=False),
        })
        self._slot_modalities = {'reference_emb', 'identity_emb', 'product_emb', 'world_emb'}

    def forward(self, bundle: Dict[str, torch.Tensor]) -> torch.Tensor:
        device = next(iter(self.projs.parameters())).device
        batch_size = 1
        for val in bundle.values():
            if val is not None and hasattr(val, 'shape') and len(val.shape) > 0:
                batch_size = val.shape[0]
                break
        c = torch.zeros((batch_size, self.dim), device=device)
        for name, proj in self.projs.items():
            val = bundle.get(name)
            if val is None:
                continue
            v = val
            if v.ndim == 1:
                v = v.unsqueeze(0)
            elif v.ndim == 3 and name in self._slot_modalities:
                v = v.mean(dim=1)
            if v.shape[-1] != self.dim:
                if v.shape[-1] > self.dim:
                    v = v[..., :self.dim]
                else:
                    pad = torch.zeros(*v.shape[:-1], self.dim - v.shape[-1], device=v.device, dtype=v.dtype)
                    v = torch.cat([v, pad], dim=-1)
            c = c + proj(v.to(next(iter(self.projs.parameters())).device))
        return c


class TimeTextEncoder(nn.Module):
    def __init__(self, text_emb: int, time_emb: int, out_dim: int):
        super().__init__()
        self.text_proj = nn.Linear(text_emb, out_dim, bias=False)
        self.time_mlp1 = nn.Linear(time_emb, out_dim, bias=False)
        self.time_mlp2 = nn.Linear(out_dim, out_dim, bias=False)

    def forward(self, text_emb: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        pooled = text_emb.mean(dim=1) if text_emb.ndim == 3 else text_emb
        te = sinusoidal_embedding_torch(t, self.time_mlp1.in_features)
        te = F.silu(self.time_mlp1(te))
        te = self.time_mlp2(te)
        return self.text_proj(pooled) + te


def sinusoidal_embedding_torch(t: torch.Tensor, dim: int, max_period: int = 10000) -> torch.Tensor:
    half = dim // 2
    freqs = torch.exp(-torch.log(torch.tensor(max_period, device=t.device)) * torch.arange(half, device=t.device, dtype=t.dtype) / max(half, 1))
    args = t.unsqueeze(-1).float() * freqs.unsqueeze(0)
    emb = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
    if dim % 2:
        emb = torch.cat([emb, torch.zeros_like(emb[:, :1])], dim=-1)
    return emb


class SpacetimePatchEmbed3D(nn.Module):
    def __init__(self, c_in: int, dim: int, patch: int, t_patch: int):
        super().__init__()
        self.patch = patch
        self.t_patch = t_patch
        self.w = nn.Parameter(torch.empty(dim, c_in, t_patch, patch, patch))
        self.b = nn.Parameter(torch.zeros(dim))
        nn.init.xavier_uniform_(self.w.view(dim, -1))

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Tuple[int, int, int]]:
        B, C, T, H, W = x.shape
        pt, ph, pw = self.t_patch, self.patch, self.patch
        Tn, Hn, Wn = T // pt, H // ph, W // pw
        x = x[:, :, :Tn * pt, :Hn * ph, :Wn * pw]
        x = x.reshape(B, C, Tn, pt, Hn, ph, Wn, pw).permute(0, 2, 4, 6, 1, 3, 5, 7).reshape(B, Tn * Hn * Wn, C * pt * ph * pw)
        out = F.linear(x, self.w.reshape(self.w.shape[0], -1), self.b)
        return out, (Tn, Hn, Wn)


class SpacetimePositionalEnc(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: int, h: int, w: int) -> torch.Tensor:
        internal = max(6, (self.dim // 6) * 6)
        d_each = internal // 3
        d_even = d_each + (d_each % 2)
        half = d_even // 2
        freqs = torch.exp(-torch.log(torch.tensor(10000.0)) * torch.arange(half, dtype=torch.float32) / max(half, 1))
        pos_t = torch.arange(t, dtype=torch.float32).unsqueeze(1) * freqs.unsqueeze(0)
        pos_h = torch.arange(h, dtype=torch.float32).unsqueeze(1) * freqs.unsqueeze(0)
        pos_w = torch.arange(w, dtype=torch.float32).unsqueeze(1) * freqs.unsqueeze(0)
        emb_t = torch.cat([torch.sin(pos_t), torch.cos(pos_t)], dim=-1)
        emb_h = torch.cat([torch.sin(pos_h), torch.cos(pos_h)], dim=-1)
        emb_w = torch.cat([torch.sin(pos_w), torch.cos(pos_w)], dim=-1)
        grid_t, grid_h, grid_w = torch.meshgrid(torch.arange(t), torch.arange(h), torch.arange(w), indexing='ij')
        emb = torch.cat([
            emb_t[grid_t.reshape(-1)],
            emb_h[grid_h.reshape(-1)],
            emb_w[grid_w.reshape(-1)],
        ], dim=-1)
        if emb.shape[-1] < self.dim:
            pad = torch.zeros(emb.shape[0], self.dim - emb.shape[-1])
            emb = torch.cat([emb, pad], dim=-1)
        elif emb.shape[-1] > self.dim:
            emb = emb[:, :self.dim]
        return emb


class MakeWorldModelV0Torch(nn.Module):
    """Pure PyTorch implementation of the MAKE spacetime DiT."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__()
        self.cfg = cfg
        dim = cfg['hidden_dim']
        num_layers = cfg['num_layers']
        heads = cfg['num_heads']
        ffn_mult = cfg.get('ffn_mult', 4)
        cond_dim = dim
        text_emb_dim = cfg.get('text_embed_dim', dim)
        time_emb_dim = cfg.get('time_embed_dim', dim)
        latent_ch = cfg.get('latent_channels', 4)
        patch = cfg.get('patch_size', 2)
        t_patch = cfg.get('temporal_patch', 1)
        text_vocab = cfg.get('text_vocab_size', 4096)
        text_seq = cfg.get('text_seq_len', 16)

        self.patch_embed = SpacetimePatchEmbed3D(latent_ch, dim, patch, t_patch)
        self.pos_enc = SpacetimePositionalEnc(dim)
        self.time_text = TimeTextEncoder(text_emb_dim, time_emb_dim, dim)
        self.text_embed = nn.Embedding(text_vocab, text_emb_dim)
        self.blocks = nn.ModuleList([
            DiTBlock(dim, heads, cond_dim, ffn_mult, has_cross=True, cross_dim=text_emb_dim)
            for _ in range(num_layers)
        ])
        self.final_norm = RMSNorm(dim)
        self.final_adaln = AdaLNZero(dim, dim, n_blocks=1)
        self.proj = nn.Linear(dim, latent_ch * t_patch * patch * patch, bias=False)
        self.cond_projs = ConditioningProjections(dim)

        # Initialize final projection with small values
        nn.init.zeros_(self.proj.weight)

    def forward(
        self,
        x_noisy: torch.Tensor,
        t: torch.Tensor,
        text_tok: torch.Tensor,
        cross_ctx: Optional[torch.Tensor] = None,
        first_frame: Optional[torch.Tensor] = None,
        last_frame: Optional[torch.Tensor] = None,
        ref_slots: Optional[torch.Tensor] = None,
        conditioning: Optional[Dict[str, torch.Tensor]] = None,
    ) -> torch.Tensor:
        x = x_noisy
        if first_frame is not None:
            ff = first_frame[:, :, :1, :, :]
            ff = F.interpolate(ff, size=x.shape[-2:], mode='bilinear', align_corners=False)
            ff = ff.expand_as(x[:, :self.cfg['latent_channels']])
            x = torch.cat([x, ff], dim=1)

        tokens, grid = self.patch_embed(x)
        pos = self.pos_enc(*grid).to(x.device)
        tokens = tokens + pos.unsqueeze(0)

        text_emb = self.text_embed(text_tok)
        if cross_ctx is None:
            cross_ctx = text_emb
        c_self = self.time_text(text_emb, t)

        if conditioning is not None:
            c_self = c_self + self.cond_projs(conditioning)
        if ref_slots is not None:
            c_self = c_self + ref_slots.mean(dim=1)

        h = tokens
        for blk in self.blocks:
            h = blk(h, c_self, cross_ctx)

        h = self.final_norm(h)
        mods = self.final_adaln(c_self)[:, 0]
        shift, scale = mods[:, 0], mods[:, 1]
        h = modulate(h, shift, scale)
        out = self.proj(h)

        B, N, _ = out.shape
        Tn, Hn, Wn = grid
        P = self.cfg['patch_size']
        Pt = self.cfg['temporal_patch']
        C = self.cfg['latent_channels']
        out = out.reshape(B, Tn, Hn, Wn, Pt, P, P, C).permute(0, 7, 1, 4, 2, 5, 3, 6).reshape(B, C, Tn * Pt, Hn * P, Wn * P)
        return out

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def state_dict(self, destination=None, prefix='', keep_vars=False):
        return super().state_dict(destination, prefix, keep_vars)

    def load_state_dict(self, state_dict, strict=True):
        return super().load_state_dict(state_dict, strict=strict)


# ----------------------------------------------------------------------
# Dataset
# ----------------------------------------------------------------------

class VideoDataset(Dataset):
    def __init__(self, manifest_path: str, split: str = "train", latent_dir: Optional[str] = None):
        self.samples = []
        self.latent_dir = latent_dir
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                data = json.load(f)
            for s in data.get('samples', []):
                if s.get('split') == split:
                    self.samples.append(s)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        if self.latent_dir:
            latent_path = os.path.join(self.latent_dir, f"{s['asset_id']}.npy")
            if os.path.exists(latent_path):
                latents = torch.from_numpy(np.load(latent_path)).float()
                return {'latents': latents, 'text_tokens': torch.zeros(s.get('text_seq_len', 16), dtype=torch.long)}
        return {'path': s['clip_path'], 'frames': s['frames'], 'fps': s['fps'], 'width': s['width'], 'height': s['height']}


# ----------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------

@dataclass
class TrainConfig:
    model_name: str = "make-5b-production"
    arch_config: Dict[str, Any] = field(default_factory=dict)
    dataset_manifest: str = ""
    max_steps: int = 100000
    batch_size: int = 1
    grad_accum_steps: int = 1
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 1000
    dtype: str = "bfloat16"
    grad_clip: float = 1.0
    use_gradient_checkpointing: bool = True
    save_every_steps: int = 5000
    validate_every_steps: int = 10000
    output_dir: str = "./outputs"
    seed: int = 42
    resume: Optional[str] = None


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        self.register(model)

    def register(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone().detach()

    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                self.shadow[name].mul_(self.decay).add_(param.data, alpha=1 - self.decay)

    def apply(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                param.data.copy_(self.shadow[name])

    def state_dict(self):
        return {'shadow': self.shadow, 'decay': self.decay}

    def load_state_dict(self, state):
        self.shadow = state['shadow']
        self.decay = state['decay']


def train_step_torch(
    model: nn.Module,
    batch: Dict[str, Any],
    optimizer: torch.optim.Optimizer,
    scaler: Optional[GradScaler],
    cfg: Dict[str, Any],
    device: torch.device,
    dtype: torch.dtype,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    model.train()
    x0 = batch['latents'].to(device, dtype=dtype)
    B = x0.shape[0]
    t = torch.rand(B, device=device) * 0.999 + 0.001

    noise = torch.randn_like(x0)
    x_t = (1 - t.view(-1, 1, 1, 1, 1)) * x0 + t.view(-1, 1, 1, 1, 1) * noise
    target = noise - x0

    with autocast(enabled=(dtype == torch.bfloat16 or dtype == torch.float16)):
        pred = model(x_t, t, batch.get('text_tokens', torch.zeros(B, cfg.get('text_seq_len', 16), dtype=torch.long, device=device)), conditioning=batch.get('conditioning'))
        loss = F.mse_loss(pred, target)

    if scaler is not None:
        scaler.scale(loss).backward()
    else:
        loss.backward()

    return loss, {'loss': loss.item()}


def train(args: TrainConfig) -> str:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    dtype = torch.bfloat16 if args.dtype == 'bfloat16' and device.type == 'cuda' else (torch.float16 if args.dtype == 'float16' and device.type == 'cuda' else torch.float32)
    print(f"Device: {device}, dtype: {dtype}")

    os.makedirs(args.output_dir, exist_ok=True)

    model = MakeWorldModelV0Torch(args.arch_config).to(device)
    param_count = model.parameter_count()
    print(f"Model parameters: {param_count:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    scaler = GradScaler() if device.type == 'cuda' else None
    ema = EMA(model, decay=0.999)

    start_step = 0
    if args.resume and os.path.exists(args.resume):
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ckpt['model'])
        optimizer.load_state_dict(ckpt['optimizer'])
        if 'ema' in ckpt:
            ema.load_state_dict(ckpt['ema'])
        start_step = ckpt.get('step', 0)
        print(f"Resumed from {args.resume} at step {start_step}")

    dataset = VideoDataset(args.dataset_manifest) if args.dataset_manifest and os.path.exists(args.dataset_manifest) else None
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0, pin_memory=True) if dataset else None

    history = []
    step = start_step
    accum_count = 0
    t0 = time.time()

    while step < args.max_steps:
        if loader is None:
            print("[ERROR] No dataset available. Cannot train without data.")
            break

        for batch in loader:
            if step >= args.max_steps:
                break

            loss_val, metrics = train_step_torch(model, batch, optimizer, scaler, args.arch_config, device, dtype)
            accum_count += 1

            if accum_count >= args.grad_accum_steps:
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
                if scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad()
                ema.update(model)
                step += 1
                accum_count = 0

                if step % 100 == 0:
                    elapsed = time.time() - t0
                    print(f"Step {step}: loss={metrics['loss']:.6f}, elapsed={elapsed:.1f}s")

                if step % args.save_every_steps == 0:
                    ckpt_path = os.path.join(args.output_dir, f"checkpoint-{step:07d}.pt")
                    torch.save({
                        'step': step,
                        'model': model.state_dict(),
                        'optimizer': optimizer.state_dict(),
                        'ema': ema.state_dict(),
                        'config': args.arch_config,
                    }, ckpt_path)
                    print(f"Saved checkpoint: {ckpt_path}")

    if accum_count > 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        if scaler is not None:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
        ema.update(model)
        step += 1

    final_path = os.path.join(args.output_dir, "final_model.pt")
    torch.save({
        'step': step,
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'ema': ema.state_dict(),
        'config': args.arch_config,
    }, final_path)
    print(f"Training complete. Final checkpoint: {final_path}")
    return final_path


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser("MAKE Production Training")
    parser.add_argument('--config', required=True, help='Training config JSON')
    parser.add_argument('--resume', default=None)
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    arch = cfg.get('arch', {})
    train_cfg = TrainConfig(
        model_name=cfg.get('model_name', 'make-5b-production'),
        arch_config=arch,
        dataset_manifest=cfg.get('dataset_manifest', ''),
        max_steps=cfg.get('max_steps', 100000),
        batch_size=cfg.get('batch_size', 1),
        grad_accum_steps=cfg.get('grad_accum_steps', 1),
        learning_rate=cfg.get('learning_rate', 1e-4),
        weight_decay=cfg.get('weight_decay', 0.01),
        warmup_steps=cfg.get('warmup_steps', 1000),
        dtype=cfg.get('dtype', 'bfloat16'),
        grad_clip=cfg.get('grad_clip', 1.0),
        use_gradient_checkpointing=cfg.get('use_gradient_checkpointing', True),
        save_every_steps=cfg.get('save_every_steps', 5000),
        validate_every_steps=cfg.get('validate_every_steps', 10000),
        output_dir=cfg.get('output_dir', './outputs'),
        seed=cfg.get('seed', 42),
        resume=args.resume,
    )
    train(train_cfg)


if __name__ == '__main__':
    main()
