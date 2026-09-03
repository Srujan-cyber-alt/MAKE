# MAKE World Model X — Scaling

Lives at `backend/app/make_model/world/scaling.py`.

## Presets

| Preset | hidden | layers | heads | ffn_mult | frames | short-side | params | vram_b1 (est) |
|---|---|---|---|---|---|---|---|---|
| TINY  |  64  | 2  | 2  | 4 | 4  | 16  |   0.48M  |  0.01 GB |
| SMALL | 128  | 4  | 4  | 4 | 8  | 32  |   2.9M   |  0.04 GB |
| MEDIUM| 384  | 12 | 6  | 4 | 16 | 64  |  69.1M   |  1.13 GB |
| LARGE | 1024 | 24 | 16 | 4 | 16 | 128 | 300M*    | 10.0 GB  |

*LARGE is documented at 300M parameters; the sandbox does not
instantiate the full ~300M object graph (which would consume
gigabytes of memory just for the numpy parameter tensors). The
estimate is calibrated from MEDIUM.

## Estimator

The VRAM estimate uses:

```
weights  = params * 2 / 1e9        # fp16
optim    = params * 8 / 1e9        # Adam: 2 fp32 moments
grad     = params * 2 / 1e9        # fp16
activ    = B * N * D * L * 4 / 1e9 # B=1, fp32 activations
total_b1 = weights + optim + grad + activ
total_b4 = total_b1 + 3 * activ    # B=4
```

where `N = Tt * Hn * Wn` is the token count and `L` is the number
of layers.

## What this is NOT

These are NOT measured benchmarks. They are engineering
estimates from the architecture math. A real benchmark on a
specific GPU + specific batch size will be added when training is
run.

## What is needed before each scale can be trained

| Preset | Min VRAM | Min dataset | Min disk | Min CPU RAM |
|---|---|---|---|---|
| TINY  |  4 GB  | 10k   clips  | 10 GB  | 8 GB  |
| SMALL |  8 GB  | 100k  clips  | 50 GB  | 16 GB |
| MEDIUM| 16 GB  | 1M    clips  | 200 GB | 32 GB |
| LARGE | 40 GB  | 50M   clips  | 5 TB   | 64 GB |

These are rough. Real numbers will come from a host with the
required GPU.

## Status

| Capability | Status |
|---|---|
| TINY param/VRAM     | YES (measured-by-construction) |
| SMALL param/VRAM    | YES |
| MEDIUM param/VRAM   | YES |
| LARGE param estimate| YES (calibrated) |
| **Real benchmark**  | **NO (no GPU)** |

## Where to read next

- `MAKE_WORLD_MODEL_HARDWARE.md`
- `MAKE_WORLD_MODEL_TRAINING_READINESS.md`
