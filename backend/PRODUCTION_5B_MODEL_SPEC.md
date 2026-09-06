# MAKE Foundation-5B Model Specification

## Architecture Overview

MAKE Foundation-5B is a spatiotemporal diffusion transformer (DiT) designed for controllable video generation.

| Property | Value |
|----------|-------|
| Total Parameters | 4,902,416,384 (~4.90B) |
| Architecture | 3D DiT with spatiotemporal patching |
| Hidden Dim | 2048 |
| Layers | 30 |
| Attention Heads | 16 |
| FFN Mult | 4 |
| Text Embed Dim | 1024 |
| Latent Channels | 4 |
| Patch Size | 2x2 |
| Temporal Patch | 1 |
| Default Frames | 16 |
| Default Short Side | 128 |
| Text Seq Len | 16 |
| Arch Version | 0.1.0 |

## Core Components

### Spatial-Temporal Attention
- Separate spatial and temporal attention blocks
- RoPE positional encoding
- QK normalization
- AdaLN-Zero conditioning

### Conditioning
- 19 modality projections
- SwiGLU FFN
- Gradient checkpointing support

### VideoVAE
- 3D encoder/decoder
- Channels: (32, 64, 128, 256)
- GroupNorm + SiLU
- KL divergence regularization
- Parameters: 2,370,571

## Production Configuration

Target training scale:
- Resolution: 128x128 (short side)
- Frames: 16
- FPS: 24
- Batch size: 1 (gradient accumulation as needed)
- Optimizer: AdamW
- LR: 1e-4
- Warmup: 1000 steps
- Scheduler: cosine
- EMA decay: 0.999
- Gradient clip: 1.0
- Precision: bfloat16 (GPU) / float32 (CPU)

## Hardware Requirements

Minimum for production training:
- GPU: NVIDIA H100 80GB or A100 80GB
- GPU count: 8+ (DDP/FSDP)
- System RAM: 512GB+
- Storage: 15TB+ for dataset

## Limitations

This is a software specification. Actual production training requires:
1. Licensed video dataset (~850K clips, ~15TB)
2. GPU cluster with CUDA
3. Trained checkpoint (currently untrained)
4. Cinematic validation (requires human evaluation)

Do not treat CPU smoke-test output as production quality.
