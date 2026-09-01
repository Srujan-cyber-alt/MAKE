# MAKE V2V ENGINE

Video-to-Video Superengine for MAKE AI Video.

## Capabilities

- Style transfer
- Character replacement
- Clothing replacement
- Background replacement
- Environment transformation
- Motion transfer
- Camera reinterpretation
- Lighting transformation
- Time-of-day transformation
- Weather transformation
- Product replacement
- Scene restyling
- Cinematic conversion

## Invariant Preservation

Example: "Make this scene cyberpunk but keep the person, movement and camera."

Only requested properties change. Requested invariants are locked.

## API

```
POST /api/v1/phase12/video-to-video
{
  "source_asset_id": "uuid",
  "project_id": "uuid",
  "prompt": "Make this scene cyberpunk but keep the person",
  "preserve_person": true,
  "preserve_product": false,
  "preserve_camera": false,
  "preserve_motion": false,
  "preserve_background": false,
  "style_strength": 0.8
}
```

## Requirements

- Backend: `VideoToVideoEngine`
- Frontend: Video upload + transformation controls + preview
