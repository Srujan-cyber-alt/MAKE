# MAKE World Model X

This is the master charter for the MAKE proprietary video model
codenamed **World Model X** (W0.1.0 in the current phase).

## Mission

Build the actual learning system that will eventually power MAKE's
proprietary neural video model:

```
LEARN THE VISUAL WORLD
  ↓
UNDERSTAND VIDEO + LANGUAGE + MOTION
  ↓
LEARN TEMPORAL RELATIONSHIPS
  ↓
LEARN CAMERA / OBJECT / CHARACTER / PRODUCT / WORLD BEHAVIOR
  ↓
GENERATE NEW VIDEO
  ↓
ITERATIVELY IMPROVE FROM MEASURED RESULTS
```

## Principles

1. **Local-only.** No cloud generation, no hosted inference, no
   remote model APIs, no external generation services.
2. **No third-party generative model.** No downloaded video
   generator, no renamed open model, no wrapped external model,
   no cloud API.
3. **No fake success.** The model state is derived from real
   artifacts on disk. A missing checkpoint is reported as
   UNTRAINED, not as INFERENCE_READY.
4. **Research discipline.** Every architectural decision documents
   WHY / ALTERNATIVES / TRADEOFFS / EXPECTED BENEFIT / MEASUREMENT.
5. **Open-source libraries as infrastructure only.** PyTorch (when
   installed on a real training host) and numpy (this sandbox) are
   engineering infrastructure. They do not contribute learned
   weights to MAKE.

## Three capabilities

| Capability | Mechanism |
|---|---|
| LEARN    | `world/training.py` (Trainer + AdamW + EMA) + `world/data_engine.py` (ingest/dedup/quality) + `world/curriculum.py` (10 stages) |
| UNDERSTAND | `world/representation.py` (Objects / People / Environment / Motion / Camera / Material) + `world/conditioning.py` (compiler) + MAKE's existing Vision Engine, IdentityEngine, ProductSystem, WorldSystem, CameraControlEngine |
| CREATE   | `world/arch.py` (MakeWorldModelV0) + `world/inference.py` (real engine) + `world/conditioning.py` (multimodal) |

The MAKE World Model never duplicates an existing MAKE system. It
calls them. For example, the conditioning compiler does NOT re-tokenize
prompts; the existing `AdvancedPromptCompiler` does. The compiler
produces a model-side tensor that the model consumes.

## Architecture at a glance

`MakeWorldModelV0` is a spacetime DiT:

```
(B, C, T, H, W) latent
  → 3D patch embed
  → + 3D sinusoidal positional encoding
  → N × DiTBlock
        adaLN-Zero
        self-attn (T*H*W tokens)
        cross-attn (text / reference / camera / motion tokens)
        SwiGLU FFN
  → final norm + adaLN
  → proj back to latent
```

Conditioning vector `c`:

```
text_tokens -> Embedding -> mean -> Linear
t          -> Sinusoidal -> MLP
c = text_proj + time_mlp
```

Reference conditioning:

```
references (R) -> 4 slots of D-dim -> cross-attention context
first_frame    -> concat along channels of the noisy latent
```

Denoising loop (research baseline):

```
x_T ~ N(0, I)
for t in [T-1 .. 0]:
    eps = model(x_t, t, text_tok, ...)
    x0  = (x_t - sqrt(1-ab[t]) * eps) / sqrt(ab[t])
    x_{t-1} = sqrt(ab[t-1]) * x0 + sqrt(1-ab[t-1]) * eps
```

## Scaling

| Preset | hidden | layers | heads | frames | short-side | params | vram_b1 (est) |
|---|---|---|---|---|---|---|---|
| TINY  |  64  | 2  | 2 | 4  | 16 | 0.48M  | 0.01 GB |
| SMALL | 128  | 4  | 4 | 8  | 32 | 2.9M   | 0.04 GB |
| MEDIUM| 384  | 12 | 6 | 16 | 64 | 69M    | 1.1 GB  |
| LARGE | 1024 | 24 | 16| 16 | 128| 300M*  | 10 GB   |

*LARGE parameter count is the documented 300M target; not instantiated
in this sandbox (it would consume too much memory at construction time).

## Reality

| State | Current |
|---|---|
| Architecture code        | READY |
| Data engine              | READY |
| Training engine          | READY |
| Distributed readiness    | READY (config only; not tested) |
| Inference engine         | READY (refuses if no checkpoint) |
| Evaluation harness       | READY (100+ prompts) |
| Audit                    | READY (returns PARTIAL) |
| **Trained weights**      | **NO** |
| **Real neural video**    | **NO** |
| **GPU on this host**     | **NONE** |
| **VRAM on this host**    | **0 GB** |
| **Training on this host**| **BLOCKED** |

## Where to read next

- `MAKE_WORLD_MODEL_ARCHITECTURE.md`  — the DiT in detail
- `MAKE_WORLD_MODEL_DATA_ENGINE.md`   — ingest / dedup / manifest
- `MAKE_WORLD_MODEL_TRAINING.md`      — training engine, distributed config
- `MAKE_WORLD_MODEL_TEMPORAL_LEARNING.md`
- `MAKE_WORLD_MODEL_CONDITIONING.md`
- `MAKE_WORLD_MODEL_SCALING.md`
- `MAKE_WORLD_MODEL_EVALUATION.md`
- `MAKE_WORLD_MODEL_HARDWARE.md`
- `MAKE_WORLD_MODEL_PROVENANCE.md`
- `MAKE_WORLD_MODEL_REALITY_REPORT.md`
- `MAKE_WORLD_MODEL_TRAINING_READINESS.md`
- `PHASE_MAKE_WORLD_MODEL_FINAL_REPORT.md`

## Most important

The repository does NOT contain a trained MAKE model. It contains
the engineering foundation that will, on a real training host,
produce the first real checkpoint.
