# MAKE GENESIS — Generation Reality & Cinematic Quality Engine

## Overview

Phase 19 transforms MAKE from a generation pipeline into a generation-aware production system. Every generation is wrapped with observability, validation, scoring, diagnosis, repair, comparison, and selection.

## Architecture

```
CREATIVE BRIEF
        ↓
MAKE GENESIS
        ↓
CAPABILITY AUDIT
        ↓
SHOT INTELLIGENCE (importance / difficulty / risk)
        ↓
BUDGET ALLOCATION
        ↓
GENERATION REALITY LAYER
        ↓
TECHNICAL VALIDATION
        ↓
VISUAL ANALYSIS (Vision Engine)
        ↓
ARTIFACT DETECTION
        ↓
CINEMATIC QUALITY SCORE
        ↓
FAILURE CLASSIFICATION
        ↓
REPAIR PLANNING
        ↓
BEST RESULT SELECTION
        ↓
FINAL QC
        ↓
MASTER
```

## Core Components

### Generation Reality Layer
Wraps every generation attempt with structured state:
- generation_id, model, provider, prompt, parameters
- status, started_at, completed_at, duration
- technical_validation, visual_analysis, quality_score, continuity_score
- failure_analysis, repair_attempts, variant_group, final_selection

### Technical Validator
Extends QualityControl with FFprobe/FFmpeg validation:
- file existence, container validity, video stream
- codec, resolution, frame rate, duration, pixel format
- frame count, corruption detection

### Artifact Detector
Structured artifact classification:
- HAND_ARTIFACT, FACE_ARTIFACT, LIMB_ARTIFACT
- OBJECT_DEFORMATION, TEXT_ARTIFACT, LOGO_ARTIFACT
- PRODUCT_DEFORMATION, TEMPORAL_FLICKER, FRAME_JUMP
- MOTION_ARTIFACT, CAMERA_ARTIFACT, BACKGROUND_ARTIFACT
- LIGHTING_ARTIFACT, IDENTITY_DRIFT, COMPOSITION_FAILURE

Each artifact includes: type, confidence, frame_range, severity, evidence, recommended_action.

### Failure Classifier
Extends Phase 16 FailureIntelligence with generation-quality-specific failures:
- PROVIDER_FAILURE, NETWORK_FAILURE, INVALID_OUTPUT
- IDENTITY_FAILURE, PRODUCT_FAILURE, TEMPORAL_FAILURE
- MOTION_FAILURE, CAMERA_FAILURE, COMPOSITION_FAILURE
- QUALITY_FAILURE, CONTINUITY_FAILURE

### Repair Planner
Generates repair strategies:
- RETRY_SAME_MODEL, CHANGE_MODEL, CHANGE_PROVIDER
- CHANGE_PROMPT, ADD_REFERENCE, CHANGE_REFERENCE
- V2V_REPAIR, FRAME_REPAIR, FULL_REGENERATION, MANUAL_REVIEW

### Shot Intelligence
Evaluates per-shot:
- priority: LOW, MEDIUM, HIGH, HERO
- difficulty: LOW, MEDIUM, HIGH, EXTREME
- risk_score: 0.0-1.0
- suggested_variant_count
- suggested_repair_attempts

### Budget Intelligence
Extends BudgetController with:
- shot-level budget allocation
- priority-based multipliers (hero = 2.5x, high = 1.5x, low = 0.5x)
- repair reserve allocation

### Reference Intelligence
Extends ReferenceManager with:
- classification: CHARACTER, PRODUCT, LOCATION, STYLE, WARDROBE, PROP, FIRST_FRAME, LAST_FRAME
- conflict detection
- per-shot reference selection

### MakeGenesis Engine
Unified orchestrator pipeline:
1. Capability Audit
2. Shot Intelligence
3. Budget Allocation
4. Generation (with reality layer)
5. Validation & Scoring
6. Repair
7. Selection
8. Assembly
9. Final QC

## API Endpoints

```
POST /api/v1/genesis/projects/{project_id}/genesis/auto
POST /api/v1/genesis/projects/{project_id}/genesis/shot-intelligence
POST /api/v1/genesis/projects/{project_id}/genesis/references/classify
POST /api/v1/genesis/projects/{project_id}/genesis/artifacts/detect
POST /api/v1/genesis/projects/{project_id}/genesis/quality/score
POST /api/v1/genesis/projects/{project_id}/genesis/technical/validate
```

## Reused Existing Systems

- ProductionEngine (Phase 18)
- ProductionGraph (Phase 18)
- QualityControl (Phase 10)
- TemporalConsistencyEngine (Phase 10)
- QualityGates (Phase 10)
- IdentityEngine (Phase 7)
- ProductConsistencyService (Phase 7)
- FailureIntelligence (Phase 16)
- BudgetController (Phase 16)
- ModelRouter4 (Phase 16)
- BestResultSelector (Phase 16)
- GenerationLearning (Phase 16)
- ModelPerformanceMemory (Phase 16)
- ReferenceManager (Phase 16)
- AdvancedPromptCompiler (Phase 9)
- CinematicQualityScore (Phase 18)
- TimelineService (Phase 17)
- ExportEngine (Phase 17)
- ProductionTemplates (Phase 18)

## Testing

Run tests:
```bash
cd backend
python3 -m pytest tests/test_phase19.py -v
```

Full regression:
```bash
python3 -m pytest tests/ -v
```

## Files Created

- `backend/app/services/generation_reality_layer.py`
- `backend/app/services/technical_validator.py`
- `backend/app/services/artifact_detector.py`
- `backend/app/services/failure_classifier.py`
- `backend/app/services/repair_planner.py`
- `backend/app/services/shot_intelligence.py`
- `backend/app/services/budget_intelligence.py`
- `backend/app/services/reference_intelligence.py`
- `backend/app/services/genesis_engine.py`
- `backend/app/routers/genesis.py`
- `backend/tests/test_phase19.py`

## Files Modified

- `backend/app/main.py` (registered genesis router)
