# MAKE VIDEO DIRECTOR

## Overview

MAKE Director is the intelligence layer that converts natural-language video requests into structured, executable production plans. It sits between user intent and the generation pipeline, ensuring that video creation is planned, reviewed, and approved before expensive generation begins.

## Architecture

```
backend/app/services/
├── director.py                  # Main orchestrator
├── intent_analyzer.py           # Extracts intent from prompts
├── creative_planner.py          # Creates creative concept and title
├── scene_planner.py             # Plans scenes based on content type
├── shot_planner.py              # Plans shots within scenes
├── asset_requirement_analyzer.py # Analyzes asset requirements
├── continuity_planner.py        # Plans continuity requirements
├── generation_requirement_planner.py # Plans generation methods
├── audio_planner.py             # Plans audio requirements
├── export_planner.py            # Plans export settings
└── director_validator.py        # Validates plan structure

backend/app/schemas/
└── director.py                  # Pydantic schemas

backend/app/routers/
└── director.py                  # API endpoints

backend/app/models/
└── models.py                    # DirectorPlan database model

frontend/src/pages/
└── Director.tsx                 # Director UI
```

## Data Flow

1. **User Input** → Natural language prompt + optional references + preferences
2. **Intent Analysis** → Extract objective, content type, tone, style, duration, platform, etc.
3. **Creative Planning** → Generate title and creative concept
4. **Scene Planning** → Determine logical scenes based on content type and duration
5. **Shot Planning** → Plan shots within each scene with camera, lighting, composition
6. **Asset Analysis** → Identify required assets (characters, products, locations, style)
7. **Continuity Planning** → Define continuity requirements across shots
8. **Generation Planning** → Determine generation methods and required capabilities
9. **Audio Planning** → Identify audio requirements (voiceover, music, SFX, ambient)
10. **Export Planning** → Determine aspect ratio, resolution, FPS, platform
11. **Validation** → Validate plan structure, duration consistency, required fields
12. **Output** → Structured DirectorPlan ready for review and approval

## Schemas

### DirectorRequest
```python
{
  "prompt": "Create a 30 second cinematic luxury watch advertisement...",
  "project_id": "optional-project-id",
  "reference_asset_ids": [],
  "character_ids": [],
  "product_ids": [],
  "location_ids": [],
  "preferences": {}
}
```

### IntentExtraction
```python
{
  "objective": "Create a 30 second cinematic luxury watch advertisement...",
  "content_type": "commercial",
  "subject": "watch",
  "audience": "luxury",
  "tone": "premium",
  "style": "cinematic",
  "story": "full original prompt",
  "total_duration_seconds": 30,
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "platform": "youtube",
  "references": [],
  "characters": ["person"],
  "products": ["product"],
  "locations": ["Tokyo"],
  "audio": {"music": true, "voiceover": true},
  "voiceover": true,
  "music": true,
  "captions": false,
  "cta": "buy now"
}
```

### ScenePlan
```python
{
  "id": "scene-1",
  "order": 0,
  "title": "Hook",
  "purpose": "Grab attention with product",
  "description": "...",
  "environment": "luxury showroom",
  "duration_seconds": 7.5,
  "shots": [...],
  "references": [],
  "characters": [],
  "products": ["product"],
  "locations": [],
  "continuity": []
}
```

### ShotPlan
```python
{
  "id": "scene-1-shot-1",
  "scene_id": "scene-1",
  "order": 0,
  "description": "Opening shot of watch in luxury showroom",
  "subject": "watch",
  "action": null,
  "environment": "luxury showroom",
  "camera": {
    "movement": "push-in",
    "lens": "macro",
    "aperture": null,
    "depth_of_field": null,
    "focus": null,
    "motion_blur": null,
    "camera_height": null,
    "camera_angle": null
  },
  "lighting": "cinematic lighting",
  "composition": "rule of thirds",
  "style": "cinematic",
  "motion": "smooth",
  "duration_seconds": 7.5,
  "references": [],
  "characters": [],
  "products": ["product"],
  "locations": [],
  "audio": [],
  "continuity": [],
  "generation": {
    "id": "scene-1-shot-1-gen",
    "method": "IMAGE_TO_VIDEO",
    "provider": null,
    "model": null,
    "required_capabilities": ["REFERENCE_IMAGES", "PRODUCT_REFERENCE"],
    "parameters": {"seed": null, "guidance_scale": 7.5}
  },
  "status": "planned"
}
```

### DirectorPlan
```python
{
  "id": "plan-uuid",
  "project_id": "project-uuid",
  "title": "Commercial Watch",
  "creative_concept": "Create a compelling product advertisement with a premium tone...",
  "objective": "Create a 30 second cinematic luxury watch advertisement...",
  "content_type": "commercial",
  "audience": "luxury",
  "tone": "premium",
  "style": "cinematic",
  "duration": 30,
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "platform": "youtube",
  "scenes": [...],
  "asset_requirements": [...],
  "continuity_requirements": [...],
  "audio_requirements": [...],
  "export_requirements": {...},
  "generation_requirements": [...],
  "status": "draft",
  "created_at": "2024-...",
  "updated_at": "2024-..."
}
```

## API Endpoints

### POST /api/v1/director/plan
Create a new director plan from a natural-language prompt.

**Request:**
```json
{
  "prompt": "Create a 30 second cinematic luxury watch advertisement...",
  "project_id": "project-uuid",
  "reference_asset_ids": [],
  "character_ids": [],
  "product_ids": [],
  "location_ids": [],
  "preferences": {}
}
```

**Response:** `201 Created`
```json
{
  "id": "plan-uuid",
  "project_id": "project-uuid",
  "title": "Commercial Watch",
  "creative_concept": "...",
  "objective": "...",
  "content_type": "commercial",
  ...
}
```

### GET /api/v1/director/plans/{plan_id}
Retrieve a specific plan.

**Response:** `200 OK`

### GET /api/v1/director/projects/{project_id}/plans
List all plans for a project.

**Response:** `200 OK`

### POST /api/v1/director/plans/{plan_id}/approve
Approve a plan for generation.

**Response:** `200 OK`

### POST /api/v1/director/plans/{plan_id}/reject
Reject a plan.

**Response:** `200 OK`

### POST /api/v1/director/plans/{plan_id}/validate
Validate a plan's structure and consistency.

**Response:** `200 OK`
```json
{
  "valid": true,
  "errors": []
}
```

### PATCH /api/v1/director/plans/{plan_id}
Update plan fields (title, duration, aspect ratio, style, status).

**Response:** `200 OK`

## Content Types

Supported content types:
- `commercial` / `advertisement`
- `cinematic`
- `social`
- `music_video`
- `explainer`
- `trailer`
- `ugc`
- `documentary`
- `storytelling`

## Camera Intelligence

Supported camera movements:
- `static`, `pan`, `tilt`, `dolly`, `truck`, `orbit`, `crane`
- `tracking`, `handheld`, `push-in`, `pull-out`, `whip-pan`
- `aerial`, `fpv`

Supported lenses:
- `14mm`, `18mm`, `24mm`, `35mm`, `50mm`, `85mm`, `135mm`
- `anamorphic`, `macro`

## Generation Methods

- `TEXT_TO_VIDEO` — Prompt-only generation
- `IMAGE_TO_VIDEO` — Image + motion
- `VIDEO_TO_VIDEO` — Video transformation
- `REFERENCE_GENERATION` — Reference-based generation
- `GENERATIVE_TRANSFORMATION` — AI-powered transformation

## Approval Workflow

Plan states:
1. `draft` — Initial state after creation
2. `approved` — User has approved for generation
3. `rejected` — User has rejected the plan
4. `executing` — Generation is in progress (future phase)
5. `completed` — Generation finished (future phase)
6. `failed` — Generation failed (future phase)

**Important:** Approving a plan does NOT start video generation. Generation is handled by a separate pipeline in a future phase.

## Validation

The DirectorPlanValidator checks:
- Valid plan structure and required IDs
- Scenes contain at least one shot
- Shot ordering and duration consistency
- Total duration matches requested duration (±20%)
- Valid aspect ratios and FPS
- Valid generation methods
- Continuity requirements have valid shot references
- No duplicate shot IDs

## Security

- All endpoints require authentication
- Project ownership is verified before plan creation
- Plan ownership is verified before retrieval/modification
- Cross-user access is denied (404/403)

## Limitations

- Intent extraction uses rule-based NLP, not LLM
- Scene planning uses templates based on content type
- Camera/lens suggestions are heuristic-based
- Generation requirements are conceptual only
- No actual video generation in Phase 4
- No audio generation in Phase 4
- No VFX or editing in Phase 4

## Testing

The Director Engine includes tests for:
- Simple, commercial, cinematic, and social prompts
- Duration, aspect ratio, and platform extraction
- Character, product, and location detection
- Reference assignment
- Scene and shot generation
- Duration validation
- Audio requirement detection
- Approval and rejection workflows
- Plan persistence and retrieval
- Unauthorized access prevention

## Examples

### Example 1: Commercial
**Input:** "Create a 30 second cinematic luxury watch advertisement. Show the watch with water droplets, orbit around it, and end with the logo."

**Output:**
- Content type: `commercial`
- Tone: `premium`
- Style: `cinematic`
- Duration: 30s
- Aspect ratio: `16:9`
- 3-4 scenes with product-focused shots
- Asset requirements: product, character
- Audio: music, voiceover

### Example 2: Social Video
**Input:** "Create a TikTok about this new shoe. Make it fun and energetic."

**Output:**
- Content type: `social`
- Platform: `tiktok`
- Tone: `energetic`
- Aspect ratio: `9:16`
- Duration: 15s (default for social)
- 3 scenes: Hook, Content, CTA
- Audio: music

### Example 3: Cinematic
**Input:** "Make a cinematic scene of a person walking through a city at night with dramatic lighting."

**Output:**
- Content type: `cinematic`
- Tone: `dramatic`
- Characters: `person`
- Locations: `city`
- 2-5 scenes with establishing and closing shots
- Asset requirements: character, location
