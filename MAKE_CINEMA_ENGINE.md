# MAKE Cinema & Generative Production Engine

## Overview

Phase 18 transforms MAKE from an AI video generator + editor into an AI-native video production studio. The system can understand a high-level creative brief and turn it into a complete production through structured pipelines.

## Architecture

```
USER CREATIVE BRIEF
        ↓
CREATIVE UNDERSTANDING
        ↓
PRODUCTION PLANNER
        ↓
STORY ENGINE
        ↓
CHARACTER SYSTEM
        ↓
WORLD SYSTEM
        ↓
PRODUCT SYSTEM
        ↓
SHOT DESIGN
        ↓
STORYBOARD
        ↓
PREVIS
        ↓
CAMERA DIRECTOR
        ↓
PERFORMANCE DIRECTOR
        ↓
GENERATION PLANNER
        ↓
UNIVERSAL MODEL ENGINE
        ↓
GENERATION
        ↓
CONTINUITY ENGINE
        ↓
QUALITY
        ↓
REPAIR
        ↓
EDIT
        ↓
VFX
        ↓
AUDIO
        ↓
COLOR
        ↓
MASTER
        ↓
EXPORT
```

## Core Components

### Production Engine
- Creates and manages production state
- Tracks all stages from brief to final master
- Integrates with existing systems

### Production Graph
- Dependency graph for production elements
- Tracks node status (pending, ready, in_progress, completed, failed)
- Propagates completion/failure through dependencies

### Shot Generation Planner
- Creates per-shot generation plans
- Compiles prompts from structured shot data
- Determines input modes (T2V, I2V, V2V, reference)
- Collects references from characters, products, world

### Continuity Engine
- Validates cross-shot continuity
- Dimensions: identity, wardrobe, product, world, lighting, camera, motion, composition
- Evidence-based scoring

### Cinematic Quality Score
- Production-level quality scoring
- Dimensions: technical, visual, continuity, camera, motion, identity, product, audio, editing, color
- Severity classification

### Production Templates
- Reusable production configurations
- Templates: product_ad, cinematic_film, social_reel, fashion_film, sports_ad
- Customizable via overrides

### MAKE AUTO CINEMA
- End-to-end production pipeline
- Stages: story → storyboard → shot planning → generation planning → continuity → quality → assembly
- Integrates with existing CreativeDirector, StoryboardEngine, ScriptEngine

### Approval Gates
- Structured approval workflow
- Stages: brief, story, storyboard, generation, edit, audio, color, qc, final
- Supports approve/reject with notes

## API Endpoints

```
POST /api/v1/cinema/projects/{project_id}/cinema/auto
GET  /api/v1/cinema/templates
GET  /api/v1/cinema/templates/{template_id}
POST /api/v1/cinema/projects/{project_id}/cinema/approve
POST /api/v1/cinema/projects/{project_id}/cinema/reject
GET  /api/v1/cinema/projects/{project_id}/cinema/continuity
POST /api/v1/cinema/projects/{project_id}/cinema/quality
POST /api/v1/cinema/projects/{project_id}/cinema/shot-plan
```

## Production Goals

- film
- short_film
- commercial
- product_ad
- music_video
- documentary
- social_video
- trailer
- teaser
- explainer
- brand_film
- fashion_film
- cinematic_montage
- product_demo
- ugc
- content_series

## Reused Existing Systems

- CreativeDirector (creative_director.py)
- StoryboardEngine (storyboard_engine.py)
- ScriptEngine (script_engine.py)
- PrevisualizationEngine (previsualization_engine.py)
- CameraControlEngine (camera_control_engine.py)
- CharacterPerformanceEngine (character_performance_engine.py)
- WorldSystem (world_system.py)
- MakeAutoMode (make_auto_mode.py)
- UniversalCommandEngine (universal_command_engine.py)
- ContinuityPlanner (continuity_planner.py)

## Testing

Run tests:
```bash
cd backend
python3 -m pytest tests/test_phase18.py -v
```

Full regression:
```bash
python3 -m pytest tests/ -v
```

## Files Created

- `backend/app/services/production_engine.py`
- `backend/app/services/production_graph.py`
- `backend/app/services/shot_generation_planner.py`
- `backend/app/services/continuity_engine.py`
- `backend/app/services/cinematic_quality_score.py`
- `backend/app/services/production_templates.py`
- `backend/app/services/make_auto_cinema.py`
- `backend/app/services/approval_gate.py`
- `backend/app/routers/cinema.py`
- `backend/tests/test_phase18.py`

## Files Modified

- `backend/app/main.py` (registered cinema router)
