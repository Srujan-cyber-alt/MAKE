"""
MAKE image subsystem (CPU-only, NumPy + Pillow).

Pure-numpy image generator. No PyTorch, no GPU required. Intended
as the honest image counterpart to the MAKE video system while
production-scale GPU compute is unavailable.

Architecture:
  - NumpyUNet: tiny UNet-style denoiser (conv + ReLU + residual)
  - GaussianDiffusion: DDPM forward / reverse process (linear beta)
  - Trainer: CPU-friendly training loop with checkpointing
  - Sampler: deterministic DDPM sampler writing PNG / JPEG
  - MakeImageRegistryBridge: registers checkpoints in the existing
    MAKE registry without any PyTorch dependency.
"""

from __future__ import annotations

from .arch.unet import NumpyUNet, NumpyUNetConfig, count_params
from .arch.diffusion import GaussianDiffusion
from .training.trainer import ImageTrainer, TrainingConfig, TrainingResult
from .inference.sampler import ImageSampler, SamplerConfig, SampleResult
from .dataset.acquire import acquire_image_dataset, DatasetInfo
from .registry_bridge import ImageRegistryBridge

__all__ = [
    "NumpyUNet",
    "NumpyUNetConfig",
    "count_params",
    "GaussianDiffusion",
    "ImageTrainer",
    "TrainingConfig",
    "TrainingResult",
    "ImageSampler",
    "SamplerConfig",
    "SampleResult",
    "acquire_image_dataset",
    "DatasetInfo",
    "ImageRegistryBridge",
]