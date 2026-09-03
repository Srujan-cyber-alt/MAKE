# MAKE VIDEO CAPABILITY MATRIX (FINAL)

## Honest Status Legend

- **VERIFIED** — Code exists and passes tests
- **REAL_LOCAL_VERIFIED** — Real local generation executed and artifact produced locally
- **LOCAL_PROCEDURAL** — FFmpeg-based procedural generation (NOT neural AI)
- **DETERMINISTIC_TEST_ONLY** — Test stub for deterministic testing only
- **RUNTIME_DEPENDENT** — Requires external runtime (provider, GPU, etc.)
- **NOT_CONFIGURED** — Not set up in current environment
- **UNAVAILABLE** — Capability cannot be provided on this hardware/runtime
- **UNVERIFIED** — Implementation exists but not verified
- **DEFERRED** — Intentionally not implemented

## Generation Capabilities

| Capability | MAKE Status | Classification |
|------------|-------------|----------------|
| Text-to-Video (FFmpeg lavfi procedural) | VERIFIED | LOCAL_PROCEDURAL |
| Text-to-Video (neural) | UNAVAILABLE | REAL_LOCAL_NEURAL (no GPU/PyTorch/diffusers) |
| Text-to-Video (cloud) | RUNTIME_DEPENDENT | Requires Runway/Pika/Higgsfield API keys |
| Image-to-Video | RUNTIME_DEPENDENT | Requires provider |
| Video-to-Video | RUNTIME_DEPENDENT | Requires provider |
| Video Extension | RUNTIME_DEPENDENT | Requires provider |
| Character Performance | RUNTIME_DEPENDENT | Requires provider |
| Object Removal | RUNTIME_DEPENDENT | Requires provider |
| Background Replacement | RUNTIME_DEPENDENT | Requires provider |
| Motion Transfer | RUNTIME_DEPENDENT | Requires provider |
| Image Generation (neural) | UNAVAILABLE | No local image model |

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
