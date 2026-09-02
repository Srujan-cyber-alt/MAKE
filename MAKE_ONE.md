# MAKE ONE — Unified Video Creation Experience

## Overview

Phase 21 integrates all existing MAKE Video capabilities into one exceptional, coherent, autonomous creative experience. MAKE ONE is the final productization layer that orchestrates existing engines without replacing them.

## Architecture

```
USER
↓
MAKE ONE (Natural Language Input)
↓
UniversalCommandEngine (Intent Parsing)
↓
MakeAutoMode / GenesisEngine (Creative Planning & Generation)
↓
ModelLab (Evidence-Based Routing)
↓
Existing Engines (Generation, Quality, Repair, Selection)
↓
TimelineService (Editing)
↓
AudioSystem / ColorLookEngine / CaptionSystem (Finishing)
↓
ExportEngine (Delivery)
↓
USER GETS RESULT
```

## Core Principle

The user should not need to understand the architecture. The user should not need to manually operate Director, Model Router, Vision, Generation Engine, Quality Engine, Repair Engine, Continuity Engine, Model Lab, Budget Engine, Editing Engine, Audio Engine, Color Engine, or Export Engine. MAKE should orchestrate them.

## Workflow

1. **Understand** — UniversalCommandEngine parses natural language
2. **Plan** — MakeAutoMode creates creative plan, storyboard, script
3. **Generate** — GenesisEngine handles generation, validation, scoring
4. **Repair** — RepairPlanner fixes failures automatically
5. **Select** — BestResultSelector chooses best variant
6. **Edit** — TimelineService assembles timeline
7. **Finish** — Audio, Color, Captions, Graphics
8. **Export** — ExportEngine delivers final master

## Modes

- **ASSISTED** — MAKE recommends, user approves
- **AUTO** — MAKE executes most decisions, user can intervene
- **FULL_AUTO** — MAKE executes end-to-end within budget/capabilities

## API Endpoints

```
POST /api/v1/make-one/projects/{project_id}/make-one
GET  /api/v1/make-one/projects/{project_id}/make-one/{one_id}
POST /api/v1/make-one/projects/{project_id}/make-one/{one_id}/cancel
POST /api/v1/make-one/projects/{project_id}/make-one/{one_id}/retry
```

## Reused Existing Systems

| System | Phase | Role in MakeOne |
|--------|-------|-----------------|
| UniversalCommandEngine | 12 | Natural language intent parsing |
| MakeAutoMode | 12 | Creative planning and execution |
| GenesisEngine | 19 | Generation quality orchestration |
| ModelLab | 20 | Evidence-based model recommendations |
| ProductionEngine | 18 | Production state management |
| ProductionGraph | 18 | Dependency tracking |
| TimelineService | 17 | Timeline assembly |
| AudioSystem | 17 | Audio mixing |
| ColorLookEngine | 17 | Color grading |
| CaptionSystem | 17 | Captions |
| ExportEngine | 17 | Final export |
| BudgetController | 16 | Budget control |
| QualityControl | 10 | Quality validation |
| TechnicalValidator | 19 | Technical validation |
| ArtifactDetector | 19 | Artifact detection |
| FailureClassifier | 19 | Failure classification |
| RepairPlanner | 19 | Repair strategy |
| ShotIntelligence | 19 | Shot priority/difficulty/risk |
| ContinuityEngine | 18 | Cross-shot continuity |
| CinematicQualityScore | 18 | Production quality scoring |

## Testing

Tests require pytest installation:
```bash
cd backend
python3 -m pytest tests/test_phase21.py -v
```

Full regression:
```bash
python3 -m pytest tests/ -v
```

## Files Created

- `backend/app/services/make_one.py`
- `backend/app/routers/make_one.py`
- `backend/tests/test_phase21.py`

## Files Modified

- `backend/app/main.py` (registered make_one router)
