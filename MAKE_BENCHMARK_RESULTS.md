# MAKE — BENCHMARK RESULTS (this session)

> All neural cases are `NOT_TESTED` because no GPU/PyTorch/diffusers/model weights are installed on this machine.
> Procedural cases are run to verify the benchmark pipeline is healthy.

## 100 Cases — Status

| Category | Cases | Executed | Passed | Failed | NOT_TESTED (HW-DEP) | Avg Score |
|----------|------:|---------:|-------:|-------:|--------------------:|-----------|
| Photorealism | 5 | 0 | 0 | 0 | 5 | n/a |
| Cinematic realism | 5 | 0 | 0 | 0 | 5 | n/a |
| Human motion | 5 | 0 | 0 | 0 | 5 | n/a |
| Facial consistency | 5 | 0 | 0 | 0 | 5 | n/a |
| Character consistency | 5 | 0 | 0 | 0 | 5 | n/a |
| Product advertising | 5 | 0 | 0 | 0 | 5 | n/a |
| Product consistency | 5 | 0 | 0 | 0 | 5 | n/a |
| Physics | 5 | 0 | 0 | 0 | 5 | n/a |
| Camera control | 5 | 0 | 0 | 0 | 5 | n/a |
| Complex motion | 5 | 0 | 0 | 0 | 5 | n/a |
| Multi-shot continuity | 5 | 0 | 0 | 0 | 5 | n/a |
| Environment/world consistency | 5 | 0 | 0 | 0 | 5 | n/a |
| Object transformation | 5 | 0 | 0 | 0 | 5 | n/a |
| Video reconstruction (V2V) | 5 | 0 | 0 | 0 | 5 | n/a |
| V2V editing | 5 | 0 | 0 | 0 | 5 | n/a |
| Image-to-video | 5 | 0 | 0 | 0 | 5 | n/a |
| Text-to-video | 5 | 0 | 0 | 0 | 5 | n/a |
| Social / UGC | 5 | 0 | 0 | 0 | 5 | n/a |
| Storytelling | 5 | 0 | 0 | 0 | 5 | n/a |
| Creative / ad generation | 5 | 0 | 0 | 0 | 5 | n/a |
| **TOTAL** | **100** | **0** | **0** | **0** | **100** | n/a |

## Why zero executions

- No GPU, no VRAM, no PyTorch, no diffusers, no neural model weights.
- All 100 cases require real neural inference.
- Running a procedural FFmpeg filter chain on a "photorealism" prompt would be misleading — it would be neither neural nor photorealism.

## Pipeline integrity (proves the runner is operational)

- Generation flow tested live in this session:
  - `POST /api/v1/auth/register` → user created
  - `POST /api/v1/auth/token` → JWT returned
  - `POST /api/v1/projects` → project created
  - `POST /api/v1/generation` → job queued, processed, completed
  - Output MP4: 22 KB, 3.0s, 320x240, h264, validated by FFprobe
  - Asset registered in DB, file served via `/api/v1/files/`
- Model-select router returned `test-provider` with score 40 (deterministic fallback).
- Director plan returned full creative concept.
- MakeOne returned `awaiting_clarification` (UniversalCommandEngine working).

## What's needed to execute the 100 cases

1. **GPU** with ≥12 GB VRAM (RTX 3060+) — recommended RTX 4090 24 GB.
2. **CUDA 12.x** + matching driver.
3. **PyTorch 2.x** + `diffusers` ≥0.27 + `transformers` + `safetensors` + `accelerate`.
4. **At least one open-weight model** (e.g. LTX-Video 2B, Wan 2.1 1.3B, HunyuanVideo 1.5B, CogVideoX-2B, or SVD-XT).
5. **LocalNeuralProvider** wired to the model (use the existing `neural_interface.py`).
6. **20+ GB disk** free.
7. Optional: API access (Higgsfield/Runway/etc.) for head-to-head comparison.

When hardware + model are available, the benchmark runner will execute all 100 cases automatically.

## How to re-run the benchmark

```bash
cd backend
.venv/bin/python3 -m app.services.benchmark_runner --suite all --platform make --output benchmark_results.json
```

For competitor runs, set the `HIGGSFIELD_API_KEY` / `RUNWAY_API_KEY` etc. and add the corresponding provider to `app/providers/__init__.py`.

## What this report does NOT claim

- Does not claim MAKE beats or loses to anyone. All neural cases are `NOT_TESTED`.
- Does not fabricate scores.
- Does not claim speed or quality that hasn't been measured.
