# MAKE QUALITY ENGINE

Generation Quality Loop for MAKE AI Video.

## Pipeline

GENERATE → ANALYZE → SCORE → DIAGNOSE → REPAIR → REGENERATE → COMPARE → KEEP BEST

## Evaluation Criteria

- Identity
- Face
- Hands
- Anatomy
- Object geometry
- Product logo
- Temporal consistency
- Lighting
- Camera
- Motion
- Composition
- Audio
- Technical quality

## Automatic Retry

Failed shots trigger automatic retries with:
- Modified prompts
- Alternative models
- Adjusted parameters

## Iteration Storage

Every iteration is stored for review and comparison.

## API

Quality evaluation is embedded in:
- `POST /api/v1/phase12/make-auto`
- `POST /api/v1/phase12/video-to-video`
- `POST /api/v1/phase12/extend-video`

## Requirements

- Backend: `QualityControl`, `IntelligentShotRepair`
- Frontend: Quality dashboard + repair controls
