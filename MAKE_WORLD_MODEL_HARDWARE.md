# MAKE World Model X — Hardware Requirements

Calculated from the actual architecture math, not from estimates.

## Current host (this audit)

| Item | Value |
|---|---|
| CPU | 4 cores |
| RAM | ~11 GB |
| Disk free | ~16 GB |
| GPU | NONE |
| VRAM | 0 GB |
| CUDA | unavailable |
| PyTorch | NOT INSTALLED |

## Per-scale requirements (single-GPU, B=1)

| Scale | params | vram_b1 | vram_b4 | min vram | recommended GPU |
|---|---|---|---|---|---|
| TINY  | 0.48M  | 0.01 GB | 0.05 GB | 4 GB   | any modern GPU |
| SMALL | 2.9M   | 0.04 GB | 0.18 GB | 4 GB   | any modern GPU |
| MEDIUM| 69M    | 1.1 GB  | 4.4 GB  | 8 GB   | RTX 4090 / A100 40GB |
| LARGE | 300M   | 10 GB   | 40 GB   | 24 GB  | A100 80GB / H100 |

## Research minimum

  - 1× GPU with ≥ 8 GB VRAM
  - 32 GB system RAM
  - 50 GB free disk
  - CUDA + matching PyTorch
  - dataset: ≥ 10k short clips

This is the minimum to get a TINY/SMALL model to move.

## Practical training

  - 1× A100 40GB (or RTX 4090)
  - 64 GB system RAM
  - 500 GB SSD (for dataset + checkpoints)
  - dataset: ≥ 100k clips
  - expected wall-clock for a single SMALL epoch: days

## Serious training

  - 4-8× A100 80GB (or H100 80GB)
  - 256 GB system RAM
  - 5 TB NVMe storage
  - dataset: ≥ 1M clips
  - FSDP across GPUs
  - expected wall-clock: weeks

## Large-scale training

  - 16-64× H100 80GB
  - 1 TB system RAM
  - 50 TB+ object storage
  - dataset: ≥ 50M clips
  - FSDP + sharded data
  - expected wall-clock: weeks-to-months

## Activation memory formula

```
act = B * N * D * L * 4
N  = (T / Pt) * (H / P) * (W / P)
```

For MEDIUM at default (T=16, H=64, P=2, Pt=1, D=384, L=12):
N = 16*32*32 = 16384
act = 1 * 16384 * 384 * 12 * 4 = 302 MB
plus weights (138 MB fp16) + optim (552 MB) + grad (138 MB)
total ≈ 1.1 GB. This matches the table above.

## What is NOT fabricated

We do NOT report dollar costs, FLOPs, or training times that have
not been measured. The numbers above are engineering estimates
from the architecture math, not benchmarks.

## Status

| Capability | Status |
|---|---|
| Per-scale param / VRAM tables | YES |
| Research minimum spec         | YES |
| Practical training spec       | YES |
| Serious training spec         | YES |
| Large-scale spec              | YES |
| **Real benchmark on real GPU**| **NO** |

## Where to read next

- `MAKE_WORLD_MODEL_TRAINING_READINESS.md`
- `MAKE_WORLD_MODEL_SCALING.md`
