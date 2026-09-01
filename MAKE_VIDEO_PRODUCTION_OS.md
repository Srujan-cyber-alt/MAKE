# MAKE VIDEO PRODUCTION OS

## Architecture

```
USER
 ↓
MAKE AUTO / UNIVERSAL COMMAND ENGINE
 ↓
MEDIA UNDERSTANDING
 ↓
CREATIVE DIRECTOR
 ↓
SCRIPT / STORYBOARD
 ↓
SHOT PLANNER
 ↓
PROMPT COMPILER
 ↓
MODEL ROUTER
 ↓
PROVIDER ADAPTER (Runway / Pika / Test)
 ↓
RESULT DOWNLOAD
 ↓
FFPROBE VALIDATION
 ↓
ASSET REGISTRATION
 ↓
QUALITY GATES
 ↓
AUTO REPAIR
 ↓
TIMELINE
 ↓
EXPORT
```

## Production Execution Flow

1. User submits natural-language command or MAKE AUTO request
2. UniversalCommandEngine parses intent, target, parameters
3. MediaUnderstanding analyzes uploaded assets
4. CreativeDirector creates production plan
5. StoryboardEngine visualizes shots
6. ScriptEngine writes dialogue/narration
7. SmartModelRouter selects best available model
8. Provider adapter submits generation job
9. Orchestrator polls for completion
10. Result downloaded to `/tmp/makeai_downloads/`
11. FFprobe validates media integrity
12. Asset registered in project with provenance
13. QualityControl evaluates output
14. IntelligentShotRepair fixes issues if needed
15. TimelineService assembles final edit
16. ExportEngine produces platform-specific output

## Systems

| System | Purpose |
|--------|---------|
| UniversalCommandEngine | NL command interpretation |
| MediaUnderstanding | Asset analysis and metadata |
| CreativeDirector | Autonomous creative planning |
| StoryboardEngine | Shot visualization |
| ScriptEngine | Story and dialogue generation |
| SmartModelRouter | Model selection with fallback |
| JobOrchestrator | Concurrent job execution with download/validation |
| Provider Adapters | Runway, Pika, TestVideoProvider |
| AssetRegistration | Persistent asset intelligence |
| VideoProcessing | FFmpeg/FFprobe operations |
| QualityControl | Technical validation |
| IntelligentShotRepair | Auto repair |
| TimelineService | NLE-style editing |
| ExportEngine | Platform-specific export |
| RealTimeProgress | SSE progress streaming |

## Verification

- 208 backend tests passing
- TypeScript passing
- Frontend production build passing
- Zero regressions
