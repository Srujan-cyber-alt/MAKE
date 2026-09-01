# MAKE IMAGE TO VIDEO

Image-to-Video Superengine for MAKE AI Video.

## Input

- One image
- Multiple images
- Character reference
- Product reference
- Environment reference
- Style reference

## Controls

- Camera movement
- Subject movement
- Facial movement
- Body movement
- Environmental motion
- Depth
- Lighting
- Lens
- Composition
- Speed
- Duration
- Keyframes

## Natural Language Examples

| Command | Action |
|---------|--------|
| "Make this image into a cinematic video." | Generates cinematic video from image |
| "Orbit around the subject." | Camera orbit |
| "Make her walk slowly." | Subject motion |
| "Use the same face as the reference." | Identity lock |
| "Keep the product identical." | Product consistency |

## API

```
POST /api/v1/phase12/image-to-video
{
  "source_asset_id": "uuid",
  "project_id": "uuid",
  "prompt": "Make this image into a cinematic video",
  "duration_seconds": 5.0,
  "character_references": ["uuid"],
  "product_references": ["uuid"],
  "world_id": "uuid",
  "brand_id": "uuid"
}
```

## Requirements

- Backend: `ImageToVideoEngine`
- Frontend: Image upload + prompt + controls
