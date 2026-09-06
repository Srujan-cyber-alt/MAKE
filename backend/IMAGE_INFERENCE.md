# MAKE Image Engine — Inference

## Inference Pipeline

MAKE Image inference is deterministic and reproducible with full provenance tracking.

## Features

- Text-to-image generation
- Image-to-image generation
- Multi-reference generation
- Resolution cascade support
- Deterministic seeding
- CFG guidance
- Euler flow matching sampling
- Provenance JSON sidecars
- Checkpoint loading

## Configuration

Inference is configured via `ImageInferenceRequest`:

- `prompt`: Text prompt
- `model_name`: Model identifier
- `checkpoint_id`: Checkpoint to load
- `seed`: Random seed
- `short_side`: Target resolution short side
- `num_inference_steps`: Sampling steps
- `sampler`: Euler
- `scheduler`: Linear
- `cfg_scale`: Classifier-free guidance scale

## Current Inference Status

| Item | Value |
|------|-------|
| Model | MAKE-native DiT (random init) |
| Resolution | 128x128 |
| Inference time | ~0.04s (CPU) |
| Output | numpy array + provenance JSON |

## Script

```bash
# Run inference
python3 -c "
from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest
engine = ImageInferenceEngine()
req = ImageInferenceRequest(prompt='a cinematic portrait', short_side=256, num_inference_steps=20)
result = engine.run(req)
print(result.output_path)
"
```

## Blocker

High-resolution inference (1024+) requires trained production weights and GPU acceleration.
