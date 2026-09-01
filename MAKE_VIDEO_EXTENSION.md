# MAKE VIDEO EXTENSION

Video Extension / Outpainting Engine for MAKE AI Video.

## Capabilities

- Extend beginning
- Extend ending
- Extend both directions
- Scene continuation
- Temporal context
- Last-frame conditioning
- First-frame conditioning
- Continuity locking
- Camera-motion continuation
- Character continuity
- Environment continuity
- Audio continuation where supported

## Natural Command

"Continue this scene for 8 seconds."

## Preservation Guarantees

- Identity
- Lighting
- Environment
- Camera language
- Motion
- Style
- Product appearance

## API

```
POST /api/v1/phase12/extend-video
{
  "source_asset_id": "uuid",
  "project_id": "uuid",
  "extend_position": "end",
  "extend_duration_seconds": 5.0,
  "preserve_identity": true,
  "preserve_camera": true,
  "preserve_lighting": true,
  "preserve_motion": true,
  "world_id": "uuid"
}
```

## Requirements

- Backend: `VideoExtensionEngine`
- Frontend: Video trim handles + extend button + prompt
