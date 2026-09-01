# MAKE AUTO

MAKE AUTO is the flagship one-click mode for MAKE AI Video.

## Concept

User enters a natural-language request. MAKE figures out how to create it.

Example:
"Make me a cinematic 30-second advertisement for this shoe."

MAKE automatically:
1. Understands the request
2. Analyzes uploaded assets
3. Creates concept
4. Writes script
5. Creates storyboard
6. Plans shots
7. Chooses models
8. Generates footage
9. Repairs failed shots
10. Edits timeline
11. Adds music
12. Adds SFX
13. Adds captions if needed
14. Color grades
15. Validates
16. Creates variants
17. Exports

## Architecture

```
USER PROMPT
    ↓
UniversalCommandEngine.parse()
    ↓
MediaUnderstanding.analyze_assets()
    ↓
CreativeDirector.create_plan()
    ↓
StoryboardEngine.generate()
    ↓
ScriptEngine.generate()
    ↓
SmartModelRouter.route()
    ↓
GenerationEngine.execute() / V2V / I2V / Extension
    ↓
TrackingService / IdentityLock / ProductConsistency
    ↓
VFXEngine / AudioSystem / ColorLookEngine
    ↓
QualityControl.evaluate()
    ↓
IntelligentShotRepair.repair_if_needed()
    ↓
TimelineService.assemble()
    ↓
ExportEngine.export()
```

## API

```
POST /api/v1/phase12/make-auto
{
  "project_id": "uuid",
  "prompt": "Create a cinematic 30-second advertisement for a luxury sneaker",
  "source_asset_ids": ["uuid"],
  "brand_id": "uuid",
  "world_id": "uuid",
  "character_ids": ["uuid"],
  "product_ids": ["uuid"],
  "approval_mode": "auto"
}
```

## Clarification

If the command is ambiguous, MAKE AUTO returns clarification questions instead of hallucinating.

## Requirements

- Backend: `MakeAutoMode` service
- Frontend: Natural language input + progress display
