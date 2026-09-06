# MAKE Image Engine — Training

## Training System

MAKE Image uses a native PyTorch training pipeline with real gradient-based optimization.

## Configuration

Training is configured via `ImageTrainingConfig`:

- `model_name`: Model identifier
- `max_steps`: Maximum training steps
- `batch_size`: Per-device batch size
- `grad_accum_steps`: Gradient accumulation steps
- `learning_rate`: AdamW learning rate
- `weight_decay`: AdamW weight decay
- `warmup_steps`: Learning rate warmup steps
- `grad_clip`: Gradient clipping norm
- `use_gradient_checkpointing`: Memory optimization
- `save_every_steps`: Checkpoint frequency
- `validate_every_steps`: Validation frequency
- `output_dir`: Output directory
- `seed`: Random seed

## Features

- Real PyTorch autograd training
- AdamW optimizer
- MSE reconstruction loss
- Gradient clipping
- EMA (Exponential Moving Average)
- Checkpoint save/load with metadata
- Deterministic seeding
- Mixed precision support (configurable)
- Gradient checkpointing support

## Current Training Status

| Item | Value |
|------|-------|
| Model | MAKE-native DiT |
| Parameters | 524,928 (TINY preset) |
| Dataset | 50 real images |
| Steps executed | 20 |
| Loss | 0.5 (random init, not converged) |
| Checkpoint | outputs/make-image-tiny_real_final.ckpt.npz |

## Blocker

Production training requires GPU compute infrastructure. CPU-only training is possible but not feasible for production-scale models or meaningful convergence.

## Scripts

```bash
# Synthetic training
python3 scripts/image_train.py --preset TINY --steps 1000

# Real image training
python3 scripts/image_train_real.py --dataset-dir ./dataset --preset TINY --steps 10000
```
