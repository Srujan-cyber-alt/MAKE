# MAKE Foundation 5B — Production Guide

## System Overview

This is the production training and inference package for the MAKE Foundation 5B video generation model.

**Architecture:** ~4.9B parameter spacetime DiT (Diffusion Transformer)
**Components:**
- `production/train.py` — Real PyTorch training with autograd, mixed precision, gradient checkpointing, EMA, DDP-ready
- `production/inference.py` — Real inference with flow matching, latent VAE decode, cinematic post-processing
- `production/dataset.py` — Autonomous legal dataset acquisition from Pixabay, Pexels, Coverr, Videvo
- `production/launcher.py` — Single entrypoint for training, inference, dataset, status
- `production/configs/production_5b.json` — Production training configuration

## Hardware Requirements

**Minimum for inference:** 1× NVIDIA GPU with 24GB VRAM (A10/A4000)
**Recommended for training:** 8× NVIDIA H100/A100 80GB with NVLink/NVSwitch
**CPU-only:** Not feasible for 5B training (requires ~80GB+ VRAM)

## Quick Start (GPU Node)

```bash
# 1. Setup environment
bash production/setup_gpu.sh

# 2. Acquire dataset
python production/dataset.py --source pixabay --max-clips 1000 --output ./dataset

# 3. Train model
python production/train.py --config production/configs/production_5b.json

# 4. Generate video
python production/inference.py --checkpoint outputs/final_model.pt --prompt "cinematic human portrait, IMAX quality" --frames 24 --short-side 1024 --resolution 4k
```

## iPhone Operation

From iOS, use any SSH client (Blink Shell, Prompt, Termius) to connect to your GPU node:

```bash
# Single command to start training
ssh user@gpu-node "cd /path/to/make && python production/train.py --config production/configs/production_5b.json"

# Check status
ssh user@gpu-node "cd /path/to/make && python production/launcher.py status"

# Generate cinematic sample
ssh user@gpu-node "cd /path/to/make && python production/inference.py --checkpoint outputs/final_model.pt --frames 24 --resolution 4096"
```

## Dataset Sources (Legally Usable)

| Source | License | Commercial Use | Attribution |
|--------|---------|----------------|-------------|
| Pixabay | Pixabay License | Yes | No |
| Pexels | Pexels License | Yes | No |
| Coverr | Coverr License | Yes | No |
| Videvo | Videvo License | Yes | May be required |
| VideoUFO | CC BY 4.0 | Yes | Yes |

## Production Features

- **Mixed precision:** BF16/FP16 training with GradScaler
- **Gradient checkpointing:** Reduces VRAM by ~40%
- **EMA:** Exponential moving average for stable inference
- **Resume:** Automatic checkpoint resume after interruption
- **DDP-ready:** Environment variable configuration for multi-node
- **Flow matching:** State-of-the-art training objective
- **Classifier-free guidance:** Configurable CFG scale at inference
- **Cinematic post-processing:** Color grading, stabilization, HDR tone mapping

## Training Configuration

Edit `production/configs/production_5b.json`:
- `max_steps`: Total training steps (100K recommended for initial training)
- `batch_size`: Per-GPU batch size (1 for 80GB H100)
- `grad_accum_steps`: Gradient accumulation (8 recommended)
- `learning_rate`: AdamW learning rate (1e-4 for 5B)
- `save_every_steps`: Checkpoint frequency

## Inference Configuration

```bash
python production/inference.py \
  --checkpoint outputs/final_model.pt \
  --prompt "cinematic video" \
  --frames 24 \
  --short-side 256 \
  --fps 24 \
  --steps 30 \
  --seed 42 \
  --cfg-scale 3.0 \
  --output cinematic_output.mp4 \
  --resolution 4096
```

## Provenance

All generated outputs include a `.provenance.json` sidecar with:
- Model checkpoint ID and SHA-256
- Architecture version and config
- Seed, prompt, and conditioning parameters
- Inference steps, sampler, scheduler
- Hardware and software environment

## Status Check

```bash
python production/launcher.py status
```

Returns JSON with:
- CUDA availability and GPU info
- Available checkpoints
- Generated outputs
- Dataset clip count
