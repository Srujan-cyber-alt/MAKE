# MAKE World Model X — Training

Lives at `backend/app/make_model/world/training.py`.

## Components

- `OptimizerConfig`    — AdamW params (lr, betas, wd, grad_clip)
- `_AdamW`             — bias-corrected AdamW
- `LRSchedule`         — warmup + cosine (or linear)
- `clip_grad_norm`     — global-norm gradient clipping
- `TrainingConfig`     — versioned training config
- `TrainingMetrics`    — per-step metric record
- `DistributedConfig`  — DDP / FSDP readiness (env-driven, untested)
- `Trainer`            — main training loop
- `ExperimentTracker`  — per-run `metrics.jsonl` + `summary.json`

## What is supported today (on CPU, numpy reference)

| Feature | Status |
|---|---|
| AdamW (bias-corrected)             | YES |
| LR warmup + cosine                  | YES |
| Gradient clipping (global L2 norm)  | YES |
| EMA over parameters                 | YES |
| Deterministic seed                  | YES |
| Validation intervals                | YES (config flag) |
| Per-step metrics                    | YES (jsonl) |
| Gradient accumulation (logical steps) | CONFIGURED |
| Mixed precision                     | CONFIGURED (no-op on CPU) |
| Activation checkpointing            | CONFIGURED (torch path) |
| Rank-aware logging                  | YES (env DDP_RANK) |
| Resume from checkpoint              | YES (CheckpointManager; legacy) |
| **Real backward pass (autograd)**   | **NOT IMPLEMENTED** (numpy reference uses a deterministic stand-in so the rest of the loop is exercised) |

The numpy reference replaces autograd with a deterministic
"training signal" (see `_FakeGrad.fake`). This is NOT a real
gradient. The torch path is the same module with autograd; the
trainer API is identical.

## Why the numpy reference exists

The whole `app/make_model/world/` package must be importable in
this sandbox (no GPU, no torch). To verify the rest of the training
pipeline (optimizer, EMA, grad clip, LR schedule, metric logging)
without a real backward pass, the reference exposes a "fake"
gradient that lets all of the surrounding machinery run.

A test (`tests/test_world_model.py::TestTraining`) runs the
reference loop end-to-end and checks the optimizer actually moves
parameters.

## Loss system

See `losses.py`. The trainer calls:

```python
parts = total_loss(
    weights,
    recon=recon,
    temporal=temporal,
    motion=motion,
    text_align=text_align,
    identity=identity,
    product=product,
    camera=camera,
    perceptual=perceptual,
)
loss = parts["total"]
```

Components with weight = 0 are NOT computed. The trainer never
invokes a loss that is off.

## Distributed training readiness

`DistributedConfig.from_env()` reads:

```
DDP_BACKEND          (default "nccl")
DDP_WORLD_SIZE       (default "1")
DDP_RANK             (default "0")
DDP_LOCAL_RANK       (default "0")
DDP_FSDP             (default "0")
DDP_FSDP_STRATEGY    (default "NO_SHARD")
DDP_ACTIVATION_CKPT  (default "0")
```

The trainer stamps every `TrainingMetrics` with `rank`. The
ExperimentTracker writes per-rank summaries.

We do NOT claim multi-node support. We DO claim that the code is
structured so multi-node support is a configuration change, not a
rewrite.

## Experiment tracking

`ExperimentTracker(run_dir)` writes:

```
<run_dir>/config.json       # full TrainingConfig
<run_dir>/metrics.jsonl     # one JSON per line per logging step
<run_dir>/summary.json      # status, total_steps, final_loss, max_samples_per_sec
```

Experiments are reproducible from `config.json` + the dataset
manifest + the checkpoint hash. Nothing else.

## Performance engineering

| Measurement | Where |
|---|---|
| samples/sec | `TrainingMetrics.samples_per_sec` |
| elapsed_seconds | `TrainingMetrics.elapsed_seconds` |
| grad_norm | `TrainingMetrics.grad_norm` |
| lr | `TrainingMetrics.lr` |
| rank | `TrainingMetrics.rank` |

GPU utilization / VRAM / dataloader time / checkpoint time will be
recorded when training is run on a real host.

## Status

| Capability | Status |
|---|---|
| AdamW (bias-corrected) | YES |
| LR warmup + cosine     | YES |
| Gradient clipping      | YES |
| EMA                    | YES |
| Deterministic seed     | YES |
| Per-step metrics       | YES |
| Rank-aware logging     | YES (config) |
| Mixed precision        | CONFIGURED |
| Activation ckpt        | CONFIGURED |
| Gradient accumulation  | CONFIGURED |
| FSDP readiness         | CONFIGURED (untested) |
| Multi-node             | NOT TESTED |
| **Real autograd**      | **NOT IMPLEMENTED (numpy ref only)** |

## Where to read next

- `MAKE_WORLD_MODEL_TEMPORAL_LEARNING.md`
- `MAKE_WORLD_MODEL_HARDWARE.md`
- `MAKE_WORLD_MODEL_TRAINING_READINESS.md`
