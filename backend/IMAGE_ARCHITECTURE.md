# MAKE Image Engine — Architecture

## Overview

MAKE Image is a MAKE-native image generation system built on a Diffusion Transformer (DiT) foundation model with flow matching. It is entirely self-contained and does not use any third-party AI generation APIs.

## Core Model

- **Architecture**: Diffusion Transformer (DiT) with cross-attention conditioning
- **Parameters**: 524,928 (TINY), scalable to billions via config presets
- **Latent representation**: 4-channel latent space with patch-based processing
- **Conditioning**: Text, image, identity, object, scene, camera, lighting, material, world-state
- **Sampling**: Euler flow matching with classifier-free guidance
- **Training**: PyTorch autograd with AdamW, EMA, gradient clipping

## Config Presets

| Preset | hidden_dim | num_layers | default_short_side |
|--------|------------|------------|-------------------|
| TINY | 64 | 2 | 32 |
| SMALL | 128 | 4 | 64 |
| MEDIUM | 384 | 12 | 128 |
| PRODUCTION | 2048 | 30 | 256 |

## Modules

- `arch.py` — Foundation model, encoders, decoders, refiner
- `conditioning.py` — Multi-modal conditioning engine
- `generation.py` — Text-to-image, image-to-image, multi-reference, cascade
- `training.py` — PyTorch training loop with real gradients
- `inference.py` — Deterministic inference with provenance
- `dataset.py` — Legal dataset acquisition with provenance
- `quality.py` — Quality gate, failure detection, photographic realism
- `evaluation.py` — Benchmark suite and human evaluation workflow
- `identity.py` — Identity genome and preservation
- `objects.py` — Object genome and manipulation
- `camera.py` — Cinema camera engine
- `lighting.py` — Lighting director
- `materials.py` — Material lab
- `world.py` — World representation, Reality DNA, World Fork, Time Machine
- `editing.py` — Intent Brush semantic editing
- `reconstruction.py` — Reality reconstruction and visual forensics
- `provenance.py` — Provenance tracking

## File Organization

```
app/make_model/image/
    arch.py
    conditioning.py
    generation.py
    training.py
    inference.py
    dataset.py
    quality.py
    evaluation.py
    identity.py
    objects.py
    camera.py
    lighting.py
    materials.py
    world.py
    editing.py
    reconstruction.py
    provenance.py

scripts/
    image_train.py
    image_train_real.py
    image_download_dataset.py
    image_launcher.py
    image_high_res.py
    image_human_eval.py

configs/
    image_tiny.json
    image_small.json
    image_medium.json
    image_production.json
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Foundation model | IMPLEMENTED |
| PyTorch autograd bridge | IMPLEMENTED |
| Multi-modal conditioning | IMPLEMENTED |
| Flow matching sampler | IMPLEMENTED |
| Real training loop | IMPLEMENTED |
| Checkpoint save/load | IMPLEMENTED |
| Dataset acquisition | IMPLEMENTED |
| Quality gate | IMPLEMENTED |
| Failure detection | IMPLEMENTED |
| Benchmark suite | IMPLEMENTED |
| Human evaluation package | IMPLEMENTED |
| High-resolution pipeline | IMPLEMENTED |
