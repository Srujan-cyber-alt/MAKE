# MAKE World Model X — Training Readiness

Generated 2026-09-03.

## Current state

| Check | Status |
|---|---|
| Architecture code        | READY |
| World representations    | READY |
| Conditioning compiler    | READY |
| Data engine              | READY |
| Curriculum               | READY |
| Hard-example mining      | READY |
| Loss system              | READY |
| Training engine (numpy)  | READY |
| Distributed config       | READY (untested) |
| Checkpointing            | READY |
| Inference engine         | READY (refuses if no checkpoint) |
| Evaluation harness       | READY |
| Audit                    | READY (PARTIAL) |
| Scaling presets          | READY (TINY..LARGE) |
| **GPU**                  | **BLOCKED — NONE** |
| **CUDA**                 | **BLOCKED — unavailable** |
| **PyTorch**              | **BLOCKED — not installed** |
| **VRAM**                 | **0 GB** |
| **Real trained weights** | **NO** |

## Overall

**BLOCKED — Reason: no GPU, no CUDA, no PyTorch on this host.**

A real training run requires:

  - GPU with CUDA (≥ 8 GB VRAM for the foundation config)
  - PyTorch installed (matching CUDA version)
  - A real video dataset with a manifest
  - Disk space for checkpoints (≥ 5 GB recommended for V0)

## Next step

Provision a host with:

  - NVIDIA GPU (RTX 4090 or A100 recommended for V0)
  - PyTorch with matching CUDA
  - ≥ 16 GB VRAM (foundation) or ≥ 24 GB (V0.1+)
  - ≥ 50 GB free disk for datasets + checkpoints
  - The current `backend/app/make_model/world/` package, unchanged

Then:

```bash
# 1. Prepare a dataset
python -m app.make_model.cli data prepare \
  --input /path/to/videos --output /path/to/manifest

# 2. Validate
python -m app.make_model.cli data validate \
  --manifest /path/to/manifest/manifest.json

# 3. Validate training readiness
python -m app.make_model.cli train validate \
  --config train_cfg.json --dataset-manifest /path/manifest.json

# 4. Run training
python -m app.make_model.cli train run --config train_cfg.json
```

The first real checkpoint will move the audit verdict to YES.
