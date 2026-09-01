# MAKE TRANSFORMATION ARCHITECTURE

## Overview

Phase 6 introduces a modular, provider-agnostic transformation architecture that extends the MAKE AI Video generation pipeline to support advanced video transformation operations.

## Core Principles

1. **Provider Agnostic** — No provider-specific logic in transformation services. Providers declare capabilities; routing selects compatible providers.
2. **Real Execution Only** — No fake/mock transformations marked as complete. Placeholder implementations are explicitly labeled.
3. **Natural Language First** — Users describe transformations in plain language; the system determines feasibility and execution plan.
4. **Pipeline Orchestration** — Complex transformations execute as multi-stage pipelines with clear status tracking.
5. **Security** — FFmpeg arguments validated, provider secrets server-side, ownership enforced on all endpoints.

## Architecture

```
Natural Language Prompt
         ↓
TransformationAnalyzer (rule-based NLP)
         ↓
TransformationPlanner (capability validation, ordering, dependencies)
         ↓
TransformationEngine (8-stage pipeline orchestrator)
         ↓
Provider Adapter (via capability routing)
         ↓
ResultValidator + AssetRegistration
```

## Services

### transformation_analyzer.py
Rule-based prompt analysis. Detects 14 transformation types, extracts targets, parameters, VFX layers, confidence scores, and capability gaps. No LLM dependency.

### transformation_planner.py
Creates structured TransformationPlan. Validates provider capabilities, orders operations by dependency, builds operation graph, surfaces actionable errors.

### transformation_engine.py
Main orchestrator. Manages 8-stage pipeline, creates Job records, handles cancellation/retry, supports batch execution, Redis-backed status tracking.

### mask_engine.py
Mask abstraction for person/object/background/face/product/sky. Supports feathering, expansion, erosion, inversion, frame-range masks. Generates FFmpeg-compatible filter chains. ML segmentation deferred to Phase 7+.

### vfx_compositor.py
FFmpeg-based VFX compositor. 13 VFX layer types, 6 blend modes, security-validated arguments. Supports opacity, intensity, duration, frame-range.

### temporal_consistency.py
Frame-to-frame validation using FFprobe scene-change detection. Returns consistency scores and flicker/discontinuity issues.

### identity_consistency.py
Redis-backed identity lock tracking, reference adherence validation, identity drift heuristics.

## Data Models

### Transformation
- id, project_id, source_asset_id, status, plan, references, temporal_constraints, identity_constraints, output_requirements, created_at, updated_at

### TransformationOperationModel
- id, transformation_id, sequence, operation_type, target, parameters, references, preserve_identity, preserve_background, strength, seed, frame_range, depends_on, status, result, error

### TransformationMask
- id, transformation_id, asset_id, mask_type, frames, metadata, created_at

### Job Extensions
- transformation_id — FK to transformations
- parent_job_id — for job graphs
- stage — current pipeline stage
- progress — completion percentage

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/v1/transformation/analyze | Analyze prompt, suggest operations |
| POST | /api/v1/transformation/plan | Create transformation plan |
| POST | /api/v1/transformation/execute | Execute transformation |
| GET | /api/v1/transformation/{id}/status | Get transformation status |
| POST | /api/v1/transformation/{id}/cancel | Cancel transformation |
| POST | /api/v1/transformation/mask | Create/update mask |
| GET | /api/v1/transformation/projects/{project_id} | List project transformations |
| POST | /api/v1/transformation/batch | Batch transformation |

All endpoints require authentication and project ownership.

## Pipeline Stages

1. **ANALYZE** — Parse prompt, identify transformation types, extract parameters
2. **DETECT** — Identify subjects/objects in source video
3. **TRACK** — Track subjects across frames
4. **MASK** — Generate masks for target regions
5. **TRANSFORM** — Execute transformation via provider
6. **COMPOSITE** — Apply VFX layers, composite masks
7. **VALIDATE** — Temporal consistency, output validation
8. **REGISTER** — Register output asset with provenance

## Provider Capabilities

New capabilities added:
- VIDEO_TO_VIDEO
- INPAINTING
- OUTPAINTING
- VFX_GENERATION
- STYLE_TRANSFER
- CAMERA_CONTROL
- IDENTITY_PRESERVATION

Providers declare these capabilities in `get_capabilities()`. TransformationPlanner validates availability before execution.

## Security

- Authentication required on all endpoints
- Project ownership enforced
- Provider secrets remain server-side
- FFmpeg arguments security-validated
- No arbitrary shell execution
- Temporary file cleanup

## Testing

16 transformation tests covering:
- Prompt analysis for all transformation types
- Plan creation and ordering
- API execution, status, cancellation
- Batch transformation
- Unauthorized access prevention
- Mask creation
- Input validation

## Frontend

Route: `/projects/:projectId/transform`

Features:
- Video source selection with preview
- Natural language prompt input
- AI analysis with confidence scoring
- Suggested operation selection
- Settings (preserve identity, preserve background, strength)
- Progress tracking with stage display
- Cancel support
- Active operations management

## Limitations

- ML-based segmentation (Phase 7+) replaced with placeholder masks
- Real motion transfer requires ML infrastructure
- VFX layers are procedural, not generative AI
- Real provider execution unverified (no credentials)

## Next Phase

Phase 7 will add:
- SAM (Segment Anything Model) integration
- Face embedding for identity preservation
- Object detection for accurate targeting
- Real mask generation from video frames
- Tracking algorithms
