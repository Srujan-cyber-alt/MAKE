"""MAKE World Model X — Video VAE.

Spatiotemporal variational autoencoder for video compression.

Architecture:
    - 3D convolutional encoder with temporal downsampling
    - Spatial downsampling
    - Reparameterization trick
    - 3D convolutional decoder with temporal upsampling
    - Stable latent scaling (log-scale standard deviation)

Tensor conventions:
    B = batch
    C = channels (3 for RGB, 4 for latent)
    T = time/frames
    H, W = spatial dimensions
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple

import numpy as np

from app.make_model.world.arch import _to_npy, _to_backend, _nn


def _to_npy(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=np.float32)


# ----------------------------------------------------------------------
# 3D Convolution building blocks
# ----------------------------------------------------------------------


class _Conv3D:
    """3D convolution with padding='same'."""

    def __init__(self, in_ch: int, out_ch: int, k: int = 3, s: int = 1, p: int = 1) -> None:
        self.in_ch = in_ch
        self.out_ch = out_ch
        self.k = k
        self.s = s
        self.p = p
        limit = 1.0 / math.sqrt(in_ch * k * k * k)
        self.w = np.random.uniform(-limit, limit, (out_ch, in_ch, k, k, k)).astype(np.float32)
        self.b = np.zeros((out_ch,), dtype=np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        B, C, T, H, W = x.shape
        if self.p > 0:
            x = np.pad(x, ((0, 0), (0, 0), (self.p, self.p), (self.p, self.p), (self.p, self.p)), mode="reflect")
        out_t = (x.shape[2] - self.k) // self.s + 1
        out_h = (x.shape[3] - self.k) // self.s + 1
        out_w = (x.shape[4] - self.k) // self.s + 1
        # im2col: extract all sliding windows
        windows = np.lib.stride_tricks.sliding_window_view(x, (self.k, self.k, self.k), axis=(2, 3, 4))
        # windows shape: (B, C, out_t, out_h, out_w, k, k, k)
        # stride and reshape to (B, out_t, out_h, out_w, C*k*k*k)
        windows = windows[:, :, ::self.s, ::self.s, ::self.s, :, :, :]
        windows = windows.reshape(B, out_t, out_h, out_w, C * self.k ** 3)
        # weight reshape: (out_ch, C*k*k*k) -> (C*k*k*k, out_ch)
        w_flat = self.w.reshape(self.out_ch, -1).T
        out = windows @ w_flat + self.b
        # (B, out_t, out_h, out_w, out_ch) -> (B, out_ch, out_t, out_h, out_w)
        return _to_backend(out.transpose(0, 4, 1, 2, 3))


class _Conv3DTranspose:
    """3D transposed convolution (upsampling)."""

    def __init__(self, in_ch: int, out_ch: int, k: int = 3, s: int = 2, p: int = 1, out_pad: int = 0) -> None:
        self.in_ch = in_ch
        self.out_ch = out_ch
        self.k = k
        self.s = s
        self.p = p
        self.out_pad = out_pad
        limit = 1.0 / math.sqrt(in_ch * k * k * k)
        self.w = np.random.uniform(-limit, limit, (in_ch, out_ch, k, k, k)).astype(np.float32)
        self.b = np.zeros((out_ch,), dtype=np.float32)

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        B, C, T, H, W = x.shape
        out_t = (T - 1) * self.s + self.k - 2 * self.p + self.out_pad
        out_h = (H - 1) * self.s + self.k - 2 * self.p + self.out_pad
        out_w = (W - 1) * self.s + self.k - 2 * self.p + self.out_pad
        # Pad input
        x_pad = np.pad(x, ((0, 0), (0, 0), (self.p, self.p), (self.p, self.p), (self.p, self.p)), mode="reflect")
        # For each output location, sum contributions from input
        out = np.zeros((B, self.out_ch, out_t, out_h, out_w), dtype=np.float32)
        # Vectorized: for each input position, scatter its weighted contribution to output
        for bt in range(B):
            for ic in range(self.in_ch):
                for tt in range(T):
                    for hh in range(H):
                        for ww in range(W):
                            val = x_pad[bt, ic, tt:tt + self.k, hh:hh + self.k, ww:ww + self.k]
                            ot_start = tt * self.s
                            oh_start = hh * self.s
                            ow_start = ww * self.s
                            for oc in range(self.out_ch):
                                out[bt, oc, ot_start:ot_start + self.k, oh_start:oh_start + self.k, ow_start:ow_start + self.k] += val * self.w[ic, oc]
        out += self.b[None, :, None, None, None]
        return _to_backend(out)


class _ResBlock3D:
    """3D residual block with GroupNorm + SiLU."""

    def __init__(self, ch: int, groups: int = 8) -> None:
        self.ch = ch
        self.groups = groups
        self.conv1 = _Conv3D(ch, ch, k=3, s=1, p=1)
        self.conv2 = _Conv3D(ch, ch, k=3, s=1, p=1)
        self.gn_w = np.ones((ch,), dtype=np.float32)
        self.gn_b = np.zeros((ch,), dtype=np.float32)
        g = max(1, min(groups, ch))
        self._groups = g
        self._group_ch = ch // g

    def __call__(self, x: Any) -> Any:
        x = _to_npy(x)
        h = _nn.group_norm(x, self.gn_w, self.gn_b, self._groups, self._group_ch)
        h = _nn.silu(h)
        h = _to_npy(self.conv1(h))
        h = _nn.group_norm(h, self.gn_w, self.gn_b, self._groups, self._group_ch)
        h = _nn.silu(h)
        h = _to_npy(self.conv2(h))
        return _to_backend(x + h)


class _Downsample3D:
    """3D downsampling via strided convolution."""

    def __init__(self, in_ch: int, out_ch: int) -> None:
        self.conv = _Conv3D(in_ch, out_ch, k=3, s=2, p=1)

    def __call__(self, x: Any) -> Any:
        return self.conv(x)


class _Upsample3D:
    """3D upsampling via transposed convolution."""

    def __init__(self, in_ch: int, out_ch: int) -> None:
        self.conv = _Conv3DTranspose(in_ch, out_ch, k=3, s=2, p=1, out_pad=1)

    def __call__(self, x: Any) -> Any:
        return self.conv(x)


# ----------------------------------------------------------------------
# Video VAE
# ----------------------------------------------------------------------


@dataclass
class VideoVAEConfig:
    """Video VAE configuration."""

    latent_channels: int = 4
    channels: Tuple[int, ...] = (64, 128, 256, 512)
    num_res_blocks: int = 2
    temporal_compression: int = 4  # 4x temporal compression
    spatial_compression: int = 8   # 8x spatial compression
    use_attention: bool = False


class VideoVAE:
    """Spatiotemporal variational autoencoder for video.

    Encodes (B, 3, T, H, W) RGB video into (B, latent_channels, t, h, w) latents.
    Decodes latents back to (B, 3, T, H, W) RGB video.

    The latent scaling is log-standard-deviation parameterization for stability:
        log_var = clamp(mlp(x), -log(2), log(2))
        z = mean + exp(0.5 * log_var) * eps
    """

    def __init__(self, cfg: Optional[VideoVAEConfig] = None) -> None:
        self.cfg = cfg or VideoVAEConfig()
        c = self.cfg
        chs = c.channels

        # Encoder
        self.enc_in = _Conv3D(3, chs[0], k=3, s=1, p=1)
        self.enc_down1 = _Downsample3D(chs[0], chs[1])
        self.enc_down2 = _Downsample3D(chs[1], chs[2])
        self.enc_down3 = _Downsample3D(chs[2], chs[3])
        self.enc_res = [_ResBlock3D(chs[3]) for _ in range(c.num_res_blocks)]
        self.enc_mid = _Conv3D(chs[3], 2 * c.latent_channels, k=3, s=1, p=1)

        # Decoder
        self.dec_in = _Conv3D(c.latent_channels, chs[3], k=3, s=1, p=1)
        self.dec_res = [_ResBlock3D(chs[3]) for _ in range(c.num_res_blocks)]
        self.dec_up1 = _Upsample3D(chs[3], chs[2])
        self.dec_up2 = _Upsample3D(chs[2], chs[1])
        self.dec_up3 = _Upsample3D(chs[1], chs[0])
        self.dec_out = _Conv3D(chs[0], 3, k=3, s=1, p=1)

        self._parameter_count: Optional[int] = None

    def parameters(self) -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
        for prefix, modules in [
            ("enc_in", [self.enc_in]),
            ("enc_down1", [self.enc_down1.conv]),
            ("enc_down2", [self.enc_down2.conv]),
            ("enc_down3", [self.enc_down3.conv]),
            ("dec_in", [self.dec_in]),
            ("dec_up1", [self.dec_up1.conv]),
            ("dec_up2", [self.dec_up2.conv]),
            ("dec_up3", [self.dec_up3.conv]),
            ("dec_out", [self.dec_out]),
        ]:
            for i, m in enumerate(modules):
                out[f"{prefix}.w"] = m.w
                out[f"{prefix}.b"] = m.b
        for i, m in enumerate(self.enc_res):
            out[f"enc_res{i}.conv1.w"] = m.conv1.w
            out[f"enc_res{i}.conv1.b"] = m.conv1.b
            out[f"enc_res{i}.conv2.w"] = m.conv2.w
            out[f"enc_res{i}.conv2.b"] = m.conv2.b
            out[f"enc_res{i}.gn_w"] = m.gn_w
            out[f"enc_res{i}.gn_b"] = m.gn_b
        for i, m in enumerate(self.dec_res):
            out[f"dec_res{i}.conv1.w"] = m.conv1.w
            out[f"dec_res{i}.conv1.b"] = m.conv1.b
            out[f"dec_res{i}.conv2.w"] = m.conv2.w
            out[f"dec_res{i}.conv2.b"] = m.conv2.b
            out[f"dec_res{i}.gn_w"] = m.gn_w
            out[f"dec_res{i}.gn_b"] = m.gn_b
        out["enc_mid.w"] = self.enc_mid.w
        out["enc_mid.b"] = self.enc_mid.b
        return out

    def load_parameters(self, params: Dict[str, np.ndarray]) -> None:
        for prefix, modules in [
            ("enc_in", [self.enc_in]),
            ("enc_down1", [self.enc_down1.conv]),
            ("enc_down2", [self.enc_down2.conv]),
            ("enc_down3", [self.enc_down3.conv]),
            ("dec_in", [self.dec_in]),
            ("dec_up1", [self.dec_up1.conv]),
            ("dec_up2", [self.dec_up2.conv]),
            ("dec_up3", [self.dec_up3.conv]),
            ("dec_out", [self.dec_out]),
        ]:
            for i, m in enumerate(modules):
                m.w = params[f"{prefix}.w"]
                m.b = params[f"{prefix}.b"]
        for i, m in enumerate(self.enc_res):
            m.conv1.w = params[f"enc_res{i}.conv1.w"]
            m.conv1.b = params[f"enc_res{i}.conv1.b"]
            m.conv2.w = params[f"enc_res{i}.conv2.w"]
            m.conv2.b = params[f"enc_res{i}.conv2.b"]
            m.gn_w = params[f"enc_res{i}.gn_w"]
            m.gn_b = params[f"enc_res{i}.gn_b"]
        for i, m in enumerate(self.dec_res):
            m.conv1.w = params[f"dec_res{i}.conv1.w"]
            m.conv1.b = params[f"dec_res{i}.conv1.b"]
            m.conv2.w = params[f"dec_res{i}.conv2.w"]
            m.conv2.b = params[f"dec_res{i}.conv2.b"]
            m.gn_w = params[f"dec_res{i}.gn_w"]
            m.gn_b = params[f"dec_res{i}.gn_b"]
        self.enc_mid.w = params["enc_mid.w"]
        self.enc_mid.b = params["enc_mid.b"]

    def parameter_count(self) -> int:
        if self._parameter_count is None:
            self._parameter_count = sum(v.size for v in self.parameters().values())
        return self._parameter_count

    def encode(self, x: Any) -> Tuple[np.ndarray, np.ndarray]:
        """Encode RGB video to latent.

        x: (B, 3, T, H, W) float32 in [0, 1]
        Returns: (mean, logvar) each (B, latent_channels, t, h, w)
        """
        x = _to_npy(x)
        h = _to_npy(_nn.silu(self.enc_in(x)))
        h = _to_npy(self.enc_down1(h))
        h = _to_npy(self.enc_down2(h))
        h = _to_npy(self.enc_down3(h))
        for block in self.enc_res:
            h = _to_npy(block(h))
        stats = _to_npy(self.enc_mid(h))
        mean, logvar = np.split(stats, 2, axis=1)
        logvar = np.clip(logvar, -math.log(2.0), math.log(2.0))
        return mean, logvar

    def decode(self, z: Any) -> np.ndarray:
        """Decode latent to RGB video.

        z: (B, latent_channels, t, h, w) float32
        Returns: (B, 3, T, H, W) float32 in [0, 1]
        """
        z = _to_npy(z)
        h = _to_npy(_nn.silu(self.dec_in(z)))
        for block in self.dec_res:
            h = _to_npy(block(h))
        h = _to_npy(self.dec_up1(h))
        h = _to_npy(self.dec_up2(h))
        h = _to_npy(self.dec_up3(h))
        out = _to_npy(self.dec_out(h))
        return np.clip(out, 0.0, 1.0)

    def reparameterize(self, mean: Any, logvar: Any, seed: int = 0) -> np.ndarray:
        """Sample z from N(mean, exp(0.5*logvar))."""
        mean = _to_npy(mean)
        logvar = _to_npy(logvar)
        rng = np.random.default_rng(seed)
        eps = rng.standard_normal(mean.shape).astype(np.float32)
        return mean + np.exp(0.5 * logvar) * eps

    def reconstruct(self, x: Any, seed: int = 0) -> np.ndarray:
        """Full encode -> sample -> decode."""
        mean, logvar = self.encode(x)
        z = self.reparameterize(mean, logvar, seed=seed)
        return self.decode(z)

    def forward(self, x: Any, seed: int = 0) -> np.ndarray:
        """Alias for reconstruct."""
        return self.reconstruct(x, seed=seed)

    def kl_loss(self, mean: Any, logvar: Any) -> np.ndarray:
        """KL divergence to standard normal."""
        mean = _to_npy(mean)
        logvar = _to_npy(logvar)
        return -0.5 * np.mean(1.0 + logvar - mean ** 2 - np.exp(logvar))

    def recon_loss(self, pred: Any, target: Any) -> np.ndarray:
        """MSE reconstruction loss."""
        p = _to_npy(pred)
        t = _to_npy(target)
        return np.mean((p - t) ** 2)
