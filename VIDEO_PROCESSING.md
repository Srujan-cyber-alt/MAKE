# MAKE AI VIDEO — VIDEO PROCESSING
## FFmpeg Integration and Local Video Operations

============================================================
SERVICE
============================================================

`VideoProcessingService` (`app/services/video_processing.py`) provides:

- `inspect_media(file_path)` → `MediaInfo`
- `trim(input_path, start, end, output_path)` → `ProcessingResult`
- `cut(input_path, start, end, output_path)` → `ProcessingResult`
- `concatenate(input_paths, output_path)` → `ProcessingResult`
- `resize(input_path, width, height, output_path)` → `ProcessingResult`
- `change_aspect_ratio(input_path, aspect_ratio, output_path)` → `ProcessingResult`
- `extract_thumbnail(input_path, timestamp, output_path)` → `ProcessingResult`
- `change_speed(input_path, speed_factor, output_path)` → `ProcessingResult`
- `remove_audio(input_path, output_path)` → `ProcessingResult`

All operations are async and timeout-protected.

============================================================
REQUIREMENTS
============================================================

- FFmpeg 4.0+ installed and in PATH
- FFprobe installed (bundled with FFmpeg)

Verify:
```bash
ffmpeg -version
ffprobe -version
```

============================================================
USAGE IN EDIT OPERATIONS
============================================================

The `EditExecutor` uses `VideoProcessingService` for operations that can be performed locally:

- **Trim**: Remove beginning/end of video
- **Cut**: Remove middle section
- **Concatenate**: Join multiple clips
- **Resize**: Change resolution
- **Aspect Ratio**: Change to 16:9, 9:16, 1:1, etc.
- **Speed**: Slow motion or fast forward
- **Mute**: Remove audio track

AI-dependent operations (object removal, background replacement, etc.) remain provider-dependent.

============================================================
ERROR HANDLING
============================================================

- `VideoProcessingError` raised on failures
- Timeout protection (30s inspect, 300s processing)
- Graceful degradation when FFmpeg is not installed
- Detailed error messages with stderr capture

============================================================
NOT SUPPORTED LOCALLY
============================================================

The following require external AI providers:
- Text-to-video generation
- Image-to-video generation
- Video-to-video transformation
- Object removal/replacement
- Background replacement
- Action transformation
- VFX effects
- Generative style transfer
