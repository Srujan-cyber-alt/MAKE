# MAKE MEDIA INTELLIGENCE

Real Multimodal Understanding Layer for MAKE AI Video.

## Supported Inputs

- Images
- Videos
- Audio
- Multiple reference images
- Multiple reference videos
- Product images
- Character references
- Scenes
- Frames
- Objects
- Faces
- Clothing
- Environments
- Logos
- Text
- Speech

## Analysis Pipeline

Every uploaded asset receives:
- Object detection
- Segmentation
- Tracking
- Scene detection
- Shot detection
- OCR
- Speech/transcription
- Audio analysis
- Visual embeddings
- Identity embeddings where supported
- Product embeddings
- Style embeddings

## Graceful Degradation

When optional ML backends are unavailable, the system:
- Logs the failure
- Continues with available capabilities
- Never pretends ML executed when it did not

## API

```
POST /api/v1/phase12/understand-asset
{
  "asset_id": "uuid",
  "asset_type": "video"
}
```

## Requirements

- Backend: `MediaUnderstanding`, `VisualAnalyzer`, `AudioSystem`
- Frontend: Asset upload + understanding display
