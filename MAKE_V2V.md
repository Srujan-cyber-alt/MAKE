# MAKE V2V

## Overview

Video-to-video transformation converts source video into a new styled/transformed video using AI provider capabilities.

## Supported V2V Transformations

- Style transfer (cinematic, anime, realistic, painting, Hollywood)
- Environment transformation (day→night, sunny→rainy, summer→winter)
- Character transformation (action, pose, movement)
- Cinematic transformation (lighting, color grade, atmosphere)
- Lighting transformation (studio, dramatic, natural, warm, cold)
- Weather transformation (rain, snow, fog, storm)
- Wardrobe transformation
- Controlled scene transformation

## Architecture

V2V flows through the TransformationEngine pipeline:

1. ANALYZE — parse prompt for transformation type and parameters
2. DETECT — identify subjects/objects (ML segmentation in Phase 7+)
3. TRACK — track across frames (Phase 7+)
4. MASK — generate masks (placeholder in Phase 6)
5. TRANSFORM — route to provider with VIDEO_TO_VIDEO capability
6. COMPOSITE — apply VFX layers if requested
7. VALIDATE — temporal consistency check
8. REGISTER — store output asset with provenance

## Provider Selection

ModelRouter selects providers based on:
- VIDEO_TO_VIDEO capability
- Duration compatibility
- Resolution compatibility
- Aspect ratio support
- Reference image support
- Provider health
- Cost/latency preferences

## Request

```json
{
  "project_id": "...",
  "source_asset_id": "...",
  "prompt": "Turn this into a cinematic action sequence with dramatic lighting",
  "operations": [
    {
      "type": "video_to_video",
      "strength": 0.8,
      "preserve_identity": true,
      "seed": 42
    }
  ],
  "references": [],
  "preferences": {}
}
```

## Limitations

- Real V2V requires provider support for VIDEO_TO_VIDEO capability
- Current TestVideoProvider supports the capability for testing
- Runway/Pika adapters need updates to declare VIDEO_TO_VIDEO and implement generation
