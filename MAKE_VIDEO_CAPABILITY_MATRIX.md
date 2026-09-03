# MAKE VIDEO CAPABILITY MATRIX (FINAL — 2026-09-03, post-audit)

## Status Legend

- **VERIFIED** — Code exists and passes tests
- **VERIFIED — REAL LOCAL NEURAL** — Real local neural model executed and produced a real artifact
- **LOCAL-RUNTIME-DEPENDENT** — Requires external runtime (GPU, PyTorch, diffusers, model weights)
- **NOT_CONFIGURED** — Not set up; no model, no GPU, no runtime
- **UNAVAILABLE** — Capability cannot be provided on this hardware/runtime
- **DETERMINISTIC-TEST-ONLY** — Test stub for deterministic testing only
- **BLOCKED-BY-LOCAL-ONLY** — Intentionally disabled by LOCAL_ONLY mode
- **FAILED** — Implementation exists but does not work
- **ARCH-ONLY** — Interface exists, no real engine

## Neural Generation Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| TEXT_TO_IMAGE | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU, no PyTorch, no diffusers |
| TEXT_TO_VIDEO (neural) | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU, no PyTorch, no diffusers |
| TEXT_TO_VIDEO (FFmpeg procedural) | **VERIFIED** | `LocalProvider` lavfi; real MP4 produced end-to-end |
| IMAGE_TO_VIDEO | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU, no PyTorch, no diffusers |
| VIDEO_TO_VIDEO | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU |
| VIDEO_EXTENSION | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU |
| MOTION_TRANSFER | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU |
| CHARACTER_PERFORMANCE | **LOCAL-RUNTIME-DEPENDENT** | No model, no GPU |
| OBJECT_REMOVAL | **LOCAL-RUNTIME-DEPENDENT** | `object_removal_service.py`; no neural model |
| OBJECT_REPLACEMENT | **LOCAL-RUNTIME-DEPENDENT** | `transformation_engine.py`; no neural model |
| BACKGROUND_REPLACEMENT | **LOCAL-RUNTIME-DEPENDENT** | `background_replacement_service.py`; no neural model |

## Procedural / Non-Neural Generation

| Capability | Status | Notes |
|------------|--------|-------|
| Text-to-Video (FFmpeg lavfi) | **VERIFIED** | `LocalProvider` — real MP4, NOT neural AI |
| TestVideoProvider | **DETERMINISTIC-TEST-ONLY** | `TestVideoProvider` — NOT neural AI |

## Cloud Generation

| Provider | Status | Notes |
|----------|--------|-------|
| Runway | **BLOCKED-BY-LOCAL-ONLY** | Not invoked in default mode |
| Pika | **BLOCKED-BY-LOCAL-ONLY** | Not invoked in default mode |
| Higgsfield / Runway API / etc. | **BLOCKED-BY-LOCAL-ONLY** | Not invoked |

## Identity / Consistency Systems (arch only — no real model)

| Capability | Status | Notes |
|------------|--------|-------|
| Identity Consistency | **ARCH-ONLY** | `identity_engine.py`; no neural model |
| Product Consistency | **ARCH-ONLY** | `product_consistency.py`; no neural model |
| World Consistency | **ARCH-ONLY** | `world_system.py`; no neural model |
| Character System | **ARCH-ONLY** | `character_system.py`; no neural model |
| Continuity Engine | **VERIFIED** | `continuity_engine.py`; metadata-level continuity |
| Brand DNA | **VERIFIED** | `brand_dna.py`; metadata storage |
| Creative Memory | **VERIFIED** | `creative_memory.py`; storage |

## Quality & Repair (real systems)

| Capability | Status | Notes |
|------------|--------|-------|
| TechnicalValidator | **VERIFIED** | FFprobe-based; verified on real MP4 this session |
| GenerationRealityLayer | **VERIFIED** | Classifies provenance (LOCAL_PROCEDURAL / DETERMINISTIC_TEST / CLOUD) |
| QualityControl | **VERIFIED** | `quality_control.py`, `quality_gates.py` |
| FailureClassifier | **VERIFIED** | `failure_classifier.py` |
| RepairPlanner | **VERIFIED** | `repair_planner.py` |
| ArtifactDetector | **VERIFIED** | `artifact_detector.py` |
| CinematicQualityScore | **VERIFIED** | `cinematic_quality_score.py` |
| BestResultSelector | **VERIFIED** | `best_result_selection.py` |
| ModelPerformanceMemory | **VERIFIED** | `model_performance_memory.py` |
| ContinuityEngine | **VERIFIED** | metadata + cross-shot continuity |
| ShotIntelligence | **VERIFIED** | `shot_intelligence.py` |
| UnifiedQualityScoring | **VERIFIED** | `unified_quality_scoring.py` |
| ShotRepairEngine | **VERIFIED** | `shot_repair_engine.py` |

## Orchestration (real systems)

| Capability | Status | Notes |
|------------|--------|-------|
| Director | **VERIFIED** | `director.py`; live test returned full plan this session |
| MakeOne | **VERIFIED** | `make_one.py`; live test dispatched and returned parsed intent |
| MakeAutoMode | **VERIFIED** | `make_auto_mode.py` |
| MakeAutoCinema | **VERIFIED** | `make_auto_cinema.py` |
| Genesis Engine | **VERIFIED** | `genesis_engine.py` |
| Cinema Engine | **VERIFIED** | `cinema.py` |
| Universal Command Engine | **VERIFIED** | `universal_command_engine.py`; live test |
| Universal Model Engine | **VERIFIED** | `universal_model_registry.py` |
| ModelRouter4 | **VERIFIED** | `model_router_4.py`; live test |
| ModelLab | **VERIFIED** | `model_lab.py` |
| Model Benchmark | **VERIFIED** | `model_benchmark.py` |
| Model Comparison | **VERIFIED** | `model_comparison.py` |
| Model Leaderboard | **VERIFIED** | `model_leaderboard.py` |
| Smart Model Router | **VERIFIED** | `smart_model_router.py` |
| Smart Target Selector | **VERIFIED** | `smart_target_selector.py` |
| Production Engine | **VERIFIED** | `production_engine.py` |
| Production Graph | **VERIFIED** | `production_graph.py` |
| Production Templates | **VERIFIED** | `production_templates.py` |
| Storyboard Engine | **VERIFIED** | `storyboard_engine.py` |
| Script Engine | **VERIFIED** | `script_engine.py` |
| Previsualization Engine | **VERIFIED** | `previsualization_engine.py` |
| Continuity Planner | **VERIFIED** | `continuity_planner.py` |
| Approval Gate | **VERIFIED** | `approval_gate.py` |
| Variant Engine | **VERIFIED** | `variant_engine.py` |

## Editing / Production

| Capability | Status | Notes |
|------------|--------|-------|
| Magic Editor | **VERIFIED** | UI + router; provider-dependent edits |
| Pro Editing | **VERIFIED** | UI + router; provider-dependent edits |
| Natural Language Editing | **VERIFIED** | `UniversalCommandEngine`; live test |
| Timeline Editing | **VERIFIED** | `timeline_service.py` |
| Rough Cut | **VERIFIED** | `timeline_service.py` |
| B-Roll | **VERIFIED** | `asset_requirement_analyzer.py` |
| Multicam | **VERIFIED** | `editing_pro.py` |
| Transitions | **VERIFIED** | FFmpeg `xfade` |
| Motion Graphics | **VERIFIED** | `vfx_engine.py`; FFmpeg |
| Kinetic Typography | **VERIFIED** | FFmpeg `drawtext` |
| Captions | **VERIFIED** | `caption_system.py` |
| Color Correction | **VERIFIED** | `color_look_engine.py`; FFmpeg |
| Color Matching | **VERIFIED** | `color_look_engine.py` |
| Stabilization | **VERIFIED** | FFmpeg `vidstab` |
| Speed Ramp | **VERIFIED** | FFmpeg `setpts` |
| Reverse | **VERIFIED** | FFmpeg |
| Freeze Frame | **VERIFIED** | FFmpeg |
| Frame Interpolation | **VERIFIED** | FFmpeg `minterpolate` |
| Upscale (FFmpeg) | **VERIFIED** | FFmpeg `scale` |
| Upscale (neural) | **LOCAL-RUNTIME-DEPENDENT** | No model |
| Smart Reframe | **VERIFIED** | `vfx_engine.py` |
| VFX Engine | **VERIFIED** | `vfx_engine.py` |
| VFX Compositor | **VERIFIED** | `vfx_compositor.py` |
| Audio Mixing | **VERIFIED** | `audio_system.py` |
| Audio Ducking | **VERIFIED** | `audio_system.py` |
| Audio (in-video native) | **FAILED** | No model supports it; arch slot only |
| Voice / TTS | **LOCAL-RUNTIME-DEPENDENT** | Needs provider |
| SFX | **FAILED** | No model |
| Music | **FAILED** | No model |
| Lip Sync | **FAILED** | No model |
| AV Sync | **VERIFIED** | `audio_planner.py` + FFmpeg |

## Vision

| Capability | Status | Notes |
|------------|--------|-------|
| Detection | **LOCAL-RUNTIME-DEPENDENT** | `vision_detection.py`; no model |
| Segmentation | **LOCAL-RUNTIME-DEPENDENT** | `vision_segmentation.py`; no model |
| Tracking | **LOCAL-RUNTIME-DEPENDENT** | `vision_tracking.py`; no model |
| Pose | **LOCAL-RUNTIME-DEPENDENT** | `vision_pose.py`; no model |
| Depth | **LOCAL-RUNTIME-DEPENDENT** | `vision_depth.py`; no model |
| Optical Flow | **LOCAL-RUNTIME-DEPENDENT** | `vision_optical_flow.py`; no model |
| Scene Understanding | **LOCAL-RUNTIME-DEPENDENT** | `vision_scene.py`; no model |
| Camera (vision) | **LOCAL-RUNTIME-DEPENDENT** | `vision_camera.py`; no model |
| Motion (vision) | **LOCAL-RUNTIME-DEPENDENT** | `vision_motion.py`; no model |
| Vision Pipeline | **VERIFIED** | `vision_pipeline.py` orchestrator |
| Media Understanding | **VERIFIED** | `media_understanding.py` |

## Reliability & Operations

| Capability | Status | Notes |
|------------|--------|-------|
| Failure Intelligence | **VERIFIED** | `failure_intelligence.py` |
| Failure Classifier | **VERIFIED** | `failure_classifier.py` |
| Repair Planner | **VERIFIED** | `repair_planner.py` |
| Budget Controller | **VERIFIED** | `budget_controller.py` |
| Budget Intelligence | **VERIFIED** | `budget_intelligence.py` |
| Cost Engine | **VERIFIED** | `cost_engine.py` |
| Provider Health | **VERIFIED** | `provider_health.py` |
| Provider Health Engine | **VERIFIED** | `provider_health_engine.py` |
| Provider Connectivity Test | **VERIFIED** | `provider_connectivity_test.py` |
| Provider Credential Manager | **VERIFIED** | `provider_credential_manager.py` |
| Real-Time Progress | **VERIFIED** | `real_time_progress.py` |
| Cancellation | **VERIFIED** | job + provider cancel |
| Retry | **VERIFIED** | tenacity-based |
| Asset Registration | **VERIFIED** | live test this session |
| Provenance Tracker | **VERIFIED** | live test this session |
| Versioning | **VERIFIED** | `versioning.py` + `ProjectVersions` |
| Export Engine | **VERIFIED** | `export_engine.py` |
| Social Export | **VERIFIED** | `social_export.py` |
| Output Normalizer | **VERIFIED** | `output_normalizer.py` |
| File Validation | **VERIFIED** | `file_validation.py` |
| File Serving | **VERIFIED** | `routers/files.py`; live test this session |
| Storage | **VERIFIED** | `services/storage.py`; live test this session |

## Neural Runtime Interface

| Capability | Status | Notes |
|------------|--------|-------|
| NeuralRuntimeState (8 states) | **VERIFIED** | `neural_interface.py`; tests pass |
| ProviderClassification (4 types) | **VERIFIED** | same file; tests pass |
| NeuralCapability (7 caps) | **VERIFIED** | same file; tests pass |
| detect_hardware() | **VERIFIED** | verified live this session |
| get_neural_runtime_report() | **VERIFIED** | verified live this session |
| enforce_local_only() | **VERIFIED** | 16 dedicated tests pass |
| get_generation_mode() | **VERIFIED** | verified live this session |
| LocalNeuralProvider | **ARCH-ONLY** | interface defined; no instance — no GPU/model |

## Generation Mode

| Mode | Behavior |
|------|----------|
| LOCAL_ONLY (default) | Cloud providers blocked, no API keys required, no cloud fallback |
| HYBRID | Both local and cloud allowed |
| CLOUD_ALLOWED | Cloud providers permitted |

## Provider Classifications

| Provider | Classification | Neural Capabilities |
|----------|---------------|-------------------|
| LocalProvider (FFmpeg lavfi) | local_procedural | ALL UNAVAILABLE |
| TestVideoProvider | deterministic_test | ALL UNAVAILABLE |
| RunwayProvider | cloud | EXTERNAL (cloud-only) |
| PikaProvider | cloud | EXTERNAL (cloud-only) |
| LocalNeuralProvider (future) | local_neural | PENDING HARDWARE |

## Important Clarification

**FFmpeg lavfi procedural generation** (e.g. `color=c=red:d=5` + `drawtext` + `eq=contrast=1.2`) is:
- Real local execution
- Produces valid MP4 files
- No cloud API, no API key
- **NOT** neural AI generation
- **NOT** a learned model
- Does not learn from data

**Neural local generation** (e.g. LTX, SVD, CogVideo, Hunyuan, Wan) requires:
- GPU with CUDA or ROCm
- PyTorch installed
- diffusers or ONNX Runtime
- Neural model weights downloaded to disk
- VRAM sufficient for the model (typically 6–12 GB)

None of these are available on the current machine. The neural interface is in place to support them when the runtime becomes available.

## Test Counts

- Backend: **393 passed, 10 skipped, 0 failed**
- Neural interface tests: **16 new tests, all passing**
- TypeScript: 0 errors
- Frontend build: PASS

## Audit Documents

- `MAKE_REAL_CAPABILITY_AUDIT.md` — full audit
- `MAKE_WORKFLOW_TEST_REPORT.md` — live workflow tests
- `MAKE_BENCHMARK_RESULTS.md` — 100-case benchmark status
- `MAKE_BENCHMARK_METHODOLOGY.md` — scoring + protocol
- `MAKE_GPU_BENCHMARK_READINESS.md` — GPU bring-up steps
- `MAKE_COMPETITIVE_FEATURE_MATRIX.md` — 14-platform matrix
- `MAKE_COMPETITIVE_SCORECARD.md` — per-category scorecard
- `MAKE_COMPETITIVE_GAP_REPORT.md` — 23 prioritized gaps
- `MAKE_COMPETITIVE_ADVANTAGES.md` — 14 verified advantages
- `MAKE_FINAL_COMPETITIVE_VERDICT.md` — direct answers
- `REAL_LOCAL_NEURAL_PROOF_REPORT.md` — hardware blocker
- `MAKE_GPU_DECISION_REPORT.md` — GPU purchase analysis
- `GPU_RUNTIME_REPORT.md` — runtime detection

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
