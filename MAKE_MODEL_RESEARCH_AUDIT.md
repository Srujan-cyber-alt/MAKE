# MAKE World Model X — Research Audit

This audit reviews the existing MAKE model foundation and identifies what
remains for a *real* learning system to be built on top of it.

## 1. Existing make_model foundation (Phase 2 deliverable)

The previous phase shipped under `backend/app/make_model/`:

- `arch/`     — 3D U-Net + temporal self-attention (legacy/baseline)
- `dataset/`  — FFmpeg-based clip manifest
- `training/` — DDPM-style MSE loss, hardware guard, AdamW
- `inference/`— refuse-untrained, real decode, provenance sidecar
- `registry/` — persistent JSON registry, SHA-256, owner=MAKE
- `state.py`  — 8-state machine
- `audit.py`  — YES/PARTIAL/NO ownership verdict
- `local_neural_provider.py` — integrated with `init_providers()`
- `api.py`    — `/api/v1/make-model/*` endpoints
- `cli.py`    — `python -m app.make_model.cli …`
- `tests/`    — 36 tests, all green

The audit endpoint returns:

  verdict=PARTIAL
  owner=MAKE
  has_checkpoint=false
  parameter_count=482,432 (TINY)
  hardware.gpu_name=""
  hardware.cuda_available=false

The previous phase correctly:
  - refused to download any pretrained weights
  - refused to label FFmpeg output as neural video
  - implemented a 3D U-Net that *can* be trained (just not yet)

## 2. Audit findings — what the 3D U-Net + DDPM prototype cannot do

The legacy architecture is **not** the right backbone for serious video
generation. Specifically:

- Conv3d scales poorly with sequence length and resolution. The
  receptive field grows linearly with depth, not logarithmically.
- Temporal self-attention is on the bottleneck only, so the model
  cannot route information between distant frames in early layers.
- There is no cross-attention, so conditioning is purely additive
  (broadcast to every spatial location). This caps text / image /
  reference / camera / motion / identity / product fidelity.
- There is no explicit first-frame, last-frame, or reference
  conditioning path.
- There is no `motion` or `camera` representation as a training
  target; the dataset only carries pixel-derived quality metrics.
- There is no curriculum and no hard-example mining.
- The denoising loop is a single-step ancestral-style baseline.
- There is no scaling ladder (TINY / SMALL / MEDIUM / LARGE).
- There is no distributed-training readiness.

## 3. Other gaps observed across the rest of MAKE

- 156 services in `app/services/`, but `app/ml/` does not exist. All
  learning logic lives in the make_model package.
- No dedup by perceptual hash.
- No provenance-based rejection of unlicensed data.
- No evaluation harness with 100+ prompts.
- No audit of "third-party model masquerading as MAKE" — there is no
  weight scanner.

These are addressed in `backend/app/make_model/world/`.

## 4. Decision: redesign the architecture

We are NOT keeping the 3D U-Net as the primary backbone.

We are introducing `MakeWorldModelV0` — a spacetime DiT-style
transformer that:

- tokenizes the latent (B, C, T, H, W) with a 3D patch embed
- adds a 3D (T, H, W) sinusoidal positional encoding
- runs N DiT blocks (adaLN-Zero) with:
  - self-attention over all (T, H, W) tokens
  - cross-attention to text / reference / conditioning
  - SwiGLU FFN
- uses a text-token embedding + sinusoidal time embedding that
  produces an additive conditioning vector c
- supports a "first-frame concat" image conditioning path
- supports R reference slots (identity / product / world)
- un-patches the output back to (B, C, T, H, W)

The legacy 3D U-Net remains in `app/make_model/arch/` as a
"baseline" and is still used for the foundation 0.1.0 docs.

## 5. What this phase adds

- `backend/app/make_model/world/arch.py`         — DiT architecture
- `backend/app/make_model/world/representation.py`— world / camera / motion / material dataclasses
- `backend/app/make_model/world/conditioning.py` — multimodal compiler
- `backend/app/make_model/world/data_engine.py`  — ingest, dedup, quality, manifest
- `backend/app/make_model/world/curriculum.py`   — 10-stage curriculum + hard-example mining
- `backend/app/make_model/world/losses.py`       — modular loss system
- `backend/app/make_model/world/training.py`     — trainer, AdamW, EMA, grad clip, distributed config
- `backend/app/make_model/world/inference.py`    — real inference engine
- `backend/app/make_model/world/audit.py`        — world ownership audit
- `backend/app/make_model/world/scaling.py`      — TINY / SMALL / MEDIUM / LARGE
- `backend/app/make_model/world/evaluation.py`   — 100+ prompt harness
- `backend/app/make_model/world/roadmap.py`      — 0.1.0 → 1.0.0
- `tests/test_world_model.py`                    — 28 tests including proof-of-training

## 6. The verdict

| Subsystem         | Status     | Why |
|-------------------|------------|-----|
| Architecture      | READY      | DiT V0 implemented, four presets, save/load round-trip |
| World rep.        | READY      | Objects / people / env / motion / camera / material dataclasses |
| Conditioning      | READY      | Text / image / ref / camera / motion / world all in one bundle |
| Data engine       | READY      | Ingest, ffprobe, dedup (aHash), quality, scene, manifest |
| Curriculum        | READY      | 10 configurable stages + weighted sampler |
| Hard-example mining | READY    | FailureRecord, HardExampleSet, WeightedSampler |
| Loss system       | READY      | 8 modular losses, total_loss aggregator |
| Training engine   | READY      | AdamW, EMA, grad clip, LR schedule, distributed config |
| Checkpointing     | READY      | numpy npz format, SHA-256, owner=MAKE enforcement |
| Inference         | READY      | Real decode, refuse-untrained, provenance sidecar |
| Evaluation        | READY      | 105 prompts, 20 categories, harness refuses if untrained |
| Ownership audit   | READY      | verdict YES / PARTIAL / NO, weight-file scanner |
| Scaling table     | READY      | TINY..LARGE with parameter and VRAM estimates |
| Roadmap           | READY      | 0.1.0 → 1.0.0 with scope / not-in-scope per version |
| **GPU training**  | **BLOCKED**| No GPU, no CUDA, no PyTorch on this host |
| **Real weights**  | **NO**     | No checkpoint has been produced |
| **Real neural video** | **NO** | No inference has produced a neural artifact |

The audit returns **PARTIAL**: all engineering modules exist; no real
checkpoint has been trained. The first real training run requires
hardware we do not currently have.

## 7. Most important finding

The repository does NOT contain a trained MAKE proprietary video model.
It contains:
  (a) a baseline 3D U-Net (from the previous phase),
  (b) a *new* spacetime DiT (this phase), and
  (c) a full training / data / inference / evaluation / audit stack.

The first real checkpoint will move the audit verdict to YES.
