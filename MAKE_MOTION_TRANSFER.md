# MAKE MOTION TRANSFER

## Overview

Motion transfer applies movement from a reference video to a target subject in the source video.

## Use Cases

- Reference dance → target character
- Reference action → target character
- Reference gesture → target character
- Reference performance → target character

## Architecture

Motion transfer flows through the TransformationEngine:

1. ANALYZE — detect motion transfer intent in prompt
2. DETECT — identify target subject (Phase 7+ ML segmentation)
3. TRACK — track subject across frames (Phase 7+)
4. MASK — isolate subject (Phase 7+)
5. TRANSFORM — route to provider with MOTION_GENERATION and FACE_ANIMATION capabilities
6. COMPOSITE — blend transformed subject back into scene
7. VALIDATE — temporal consistency check
8. REGISTER — store output asset

## Provider Requirements

Providers must declare:
- MOTION_GENERATION capability
- FACE_ANIMATION capability (for character motion)
- Reference video input support

## Request

```json
{
  "project_id": "...",
  "source_asset_id": "...",
  "prompt": "Make this person perform the dance from the reference video",
  "operations": [
    {
      "type": "motion_transfer",
      "target": {
        "type": "person",
        "description": "person in video"
      },
      "preserve_identity": true,
      "strength": 0.9
    }
  ],
  "references": ["reference-video-id"]
}
```

## Limitations

- Real motion transfer requires provider support for MOTION_GENERATION capability
- Subject tracking and mask generation are deferred to Phase 7+
- Current implementation routes to providers but does not execute real motion transfer without ML infrastructure
