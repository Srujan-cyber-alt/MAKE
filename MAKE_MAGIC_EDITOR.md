# MAKE MAGIC EDITOR

The Magic Editor is the flagship editing experience for MAKE AI Video.

## Concept

User uploads video. User types a natural-language command. The system automatically analyzes, selects target, tracks, plans, routes, generates, composites, validates, repairs, and versions.

## Supported Commands

| Command | Action |
|---------|--------|
| "Remove the man." | Object removal with inpainting |
| "Move the car to the left." | Object repositioning |
| "Make her smile." | Facial expression change |
| "Change her clothes." | Clothing replacement |
| "Replace the sky." | Background replacement |
| "Add rain." | VFX overlay |
| "Make the camera closer." | Camera reinterpretation |
| "Make him run." | Motion transfer |
| "Change the lighting to sunset." | Lighting transformation |
| "Make this look like a movie." | Cinematic color grade |
| "Extend the shot." | Video extension |
| "Change only the background." | Background-only transformation |

## Architecture

```
ANALYZE → SELECT TARGET → TRACK → PLAN → ROUTE → GENERATE → COMPOSITE → VALIDATE → REPAIR → VERSION
```

## API

```
POST /api/v1/phase12/video-to-video
POST /api/v1/phase12/extend-video
POST /api/v1/phase12/command
```

## Requirements

- Backend: `VideoToVideoEngine`, `VideoExtensionEngine`, `UniversalCommandEngine`
- Frontend: Video upload + natural language input + timeline preview
