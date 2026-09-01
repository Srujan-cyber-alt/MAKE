# MAKE VIDEO TRANSFORMATION

## Overview

MAKE Transformation Engine converts natural-language video transformation requests into executable, provider-agnostic pipelines.

## Supported Transformations

- Object removal
- Object replacement
- Background replacement
- Style transfer
- Motion transfer
- Camera transformation
- VFX application (fire, smoke, rain, snow, fog, sparks, lightning, glow, explosion, energy, atmospheric, debris, cinematic particles)
- Inpainting / outpainting
- Environment transformation (day/night, weather, season)
- Lighting transformation
- Action transformation
- Identity preservation
- Video-to-video transformation

## Usage

```
POST /api/v1/transformation/analyze
POST /api/v1/transformation/plan
POST /api/v1/transformation/execute
GET  /api/v1/transformation/{id}/status
POST /api/v1/transformation/{id}/cancel
POST /api/v1/transformation/mask
GET  /api/v1/transformation/projects/{project_id}
POST /api/v1/transformation/batch
```

## Pipeline

ANALYZE → DETECT → TRACK → MASK → TRANSFORM → COMPOSITE → VALIDATE → REGISTER

## Provider Routing

Transformations route to providers based on declared capabilities. Providers must implement capability declarations for transformation types. Missing capabilities surface as actionable errors before execution begins.

## Frontend

Route: `/projects/:projectId/transform`

Features:
- Natural language prompt input
- AI-powered analysis with confidence scoring
- Suggested operation selection
- Preserve identity / background toggles
- Strength slider
- Real-time progress tracking
- Cancel support

## Limitations

- ML-based segmentation is deferred to Phase 7+; current mask engine produces deterministic placeholder masks
- Real provider execution requires providers to declare transformation capabilities
- Identity preservation uses metadata heuristics; will be upgraded with embedding models in Phase 7
