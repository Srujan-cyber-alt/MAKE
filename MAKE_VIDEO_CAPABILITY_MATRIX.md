# MAKE VIDEO CAPABILITY MATRIX (FINAL — 2026-09-03)

## Status Legend

- **VERIFIED — REAL LOCAL NEURAL** — Real local neural model executed and produced a real artifact
- **VERIFIED** — Code exists and passes tests
- **LOCAL-RUNTIME-DEPENDENT** — Requires external runtime (GPU, PyTorch, diffusers, model weights)
- **NOT_CONFIGURED** — Not set up; no model, no GPU, no runtime
- **UNAVAILABLE** — Capability cannot be provided on this hardware/runtime
- **DETERMINISTIC-TEST-ONLY** — Test stub for deterministic testing only
- **BLOCKED-BY-LOCAL-ONLY** — Intentionally disabled by LOCAL_ONLY mode
- **FAILED** — Implementation exists but does not work

## Neural Generation Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| TEXT_TO_IMAGE | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| TEXT_TO_VIDEO | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| IMAGE_TO_VIDEO | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| VIDEO_TO_VIDEO | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| VIDEO_EXTENSION | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| MOTION_TRANSFER | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |
| CHARACTER_PERFORMANCE | **NOT_CONFIGURED** | No model, no GPU, no PyTorch, no diffusers |

## Procedural / Non-Neural Generation

| Capability | Status | Notes |
|------------|--------|-------|
| Text-to-Video (FFmpeg lavfi procedural) | **VERIFIED** | LOCAL_PROCEDURAL — NOT neural AI |
| TestVideoProvider | **DETERMINISTIC-TEST-ONLY** | NOT neural AI |

## Cloud Generation

| Provider | Status | Notes |
|----------|--------|-------|
| Runway | **BLOCKED-BY-LOCAL-ONLY** | Not invoked in default mode |
| Pika | **BLOCKED-BY-LOCAL-ONLY** | Not invoked in default mode |
| Higgsfield | **BLOCKED-BY-LOCAL-ONLY** | Not invoked; benchmark framework ready |

## Neural Runtime Interface (Future-Ready)

The `neural_interface.py` module declares the contract for future local neural generation runtimes:

| Component | Status |
|-----------|--------|
| NeuralRuntimeState enum (8 states) | IMPLEMENTED |
| ProviderClassification enum (4 types) | IMPLEMENTED |
| NeuralCapability enum (7 capabilities) | IMPLEMENTED |
| Hardware detection (nvidia-smi, torch, diffusers, onnx) | IMPLEMENTED |
| Neural runtime report | IMPLEMENTED |
| Generation mode enforcement | IMPLEMENTED |
| LOCAL_ONLY enforcement | VERIFIED |
| Future provider registration (no ModelRouter4 change) | VERIFIED |

## Generation Mode

| Mode | Behavior |
|------|----------|
| LOCAL_ONLY (default) | Cloud providers blocked, no API keys required, no cloud fallback |
| HYBRID | Both local and cloud allowed |
| CLOUD_ALLOWED | Cloud providers permitted |

## Provider Classifications

| Provider | Classification | Neural Capabilities |
|----------|---------------|-------------------|
| LocalProvider (FFmpeg lavfi) | LOCAL_PROCEDURAL | ALL UNAVAILABLE |
| TestVideoProvider | DETERMINISTIC_TEST | ALL UNAVAILABLE |
| RunwayProvider | CLOUD | EXTERNAL (cloud-only) |
| PikaProvider | CLOUD | EXTERNAL (cloud-only) |

## Production Systems

| Capability | Status |
|------------|--------|
| UniversalCommandEngine | VERIFIED |
| MakeAutoMode | VERIFIED |
| GenesisEngine | VERIFIED |
| ModelLab | VERIFIED |
| ContinuityEngine | VERIFIED |
| CinematicQualityScore | VERIFIED |
| TechnicalValidator | VERIFIED |
| ArtifactDetector | VERIFIED |
| FailureClassifier | VERIFIED |
| RepairPlanner | VERIFIED |
| ShotIntelligence | VERIFIED |
| BudgetIntelligence | VERIFIED |
| ReferenceIntelligence | VERIFIED |
| BestResultSelector | VERIFIED |
| TimelineService | VERIFIED |
| AudioSystem | VERIFIED |
| ColorLookEngine | VERIFIED |
| CaptionSystem | VERIFIED |
| ExportEngine | VERIFIED |
| MAKE ONE | VERIFIED |

## Important Clarification

**FFmpeg lavfi procedural generation** (e.g., `color=c=red:d=5` + `drawtext` + `eq=contrast=1.2`) is:
- ✅ Real local execution
- ✅ Produces valid MP4 files
- ✅ No cloud API, no API key
- ❌ NOT neural AI generation
- ❌ NOT a learned model
- ❌ Does not learn from data

**Neural local generation** (e.g., SVD, CogVideo, Hunyuan, LTX, Mochi) requires:
- GPU with CUDA or ROCm
- PyTorch installed
- diffusers or ONNX Runtime
- Neural model weights downloaded to disk
- VRAM sufficient for the model (typically 6-12 GB)

None of these are available on the current machine. The neural interface is in place to support them when the runtime becomes available.

## Test Counts

- Backend: 393 passed, 10 skipped, 0 failed
- Neural interface tests: 16 new tests, all passing
- TypeScript: 0 errors
- Frontend build: PASS
