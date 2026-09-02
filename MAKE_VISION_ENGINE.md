# MAKE VISION & PERFORMANCE ENGINE
Phase 15 — Computer Vision & Visual Intelligence Layer

## Architecture

```
UPLOAD MEDIA
      ↓
MEDIA UNDERSTANDING
      ↓
SCENE DETECTION
      ↓
OBJECT / PERSON DETECTION
      ↓
SEGMENTATION / MATTING
      ↓
TRACKING
      ↓
POSE / MOTION UNDERSTANDING
      ↓
CAMERA MOTION UNDERSTANDING
      ↓
IDENTITY / PRODUCT CONSISTENCY
      ↓
STRUCTURED VISUAL REPRESENTATION
      ↓
TRANSFORMATION / PERFORMANCE / GENERATION
      ↓
QUALITY VALIDATION
```

## Backend Services

### Core Vision Services
- `vision_runtime.py` — Hardware/backend capability detection (CPU, GPU, CUDA, MPS, ONNX, OpenCV, PyTorch)
- `vision_model_registry.py` — Model registry with 9 default models (YOLO, SAM, SAM2, ByteTrack, OpenCV, rembg)
- `vision_detection.py` — Object detection abstraction (YOLO, ONNX, OpenCV Haar, Null)
- `vision_segmentation.py` — Segmentation abstraction (SAM, SAM2, rembg, OpenCV MOG2, Null)
- `vision_tracking.py` — Multi-object tracking (OpenCV CSRT, Null)
- `vision_pose.py` — Pose estimation (OpenCV Haar upper body, Null)
- `vision_motion.py` — Motion extraction via optical flow (OpenCV Farneback, Null)
- `vision_camera.py` — Camera motion analysis (OpenCV Farneback, Null)
- `vision_optical_flow.py` — Optical flow abstraction (Farneback, TV-L1, Null)
- `vision_depth.py` — Optional depth estimation (Null by default)
- `vision_scene.py` — Scene understanding with structured SceneSegment output
- `vision_pipeline.py` — Unified pipeline orchestrating all stages

### Database
- `models/models.py` — Added `VisionAnalysis` model
- `alembic/versions/004_add_vision_analyses_table.py` — Migration for vision_analyses table

### API Router
- `routers/vision.py` — Endpoints:
  - `GET /vision/runtime` — Capability report
  - `GET /vision/models` — Model registry
  - `POST /vision/assets/{id}/analyze` — Run analysis
  - `GET /vision/assets/{id}/analysis` — Get cached/latest analysis
  - `GET /vision/jobs/{id}` — Get analysis job status

## Frontend

### Components
- `VisionPanel.tsx` — Right panel showing vision capabilities and analysis status
- Integrated into `Studio.tsx` — Shows vision capabilities and asset analysis

## Creation Modes

1. CREATE — Prompt → creative plan → shots → generation → QC
2. EDIT — Existing video → natural language editing
3. TRANSFORM — Existing media → object/background/style/motion transformation
4. ANIMATE — Image/person/product → motion/performance
5. EXTEND — Existing video → continuation
6. REMIX — Existing video → alternative creative versions
7. AUTO — MAKE independently executes complete workflow

## Command Flow

1. User enters natural-language command in CreateBar
2. Frontend sends to `/api/v1/studio/projects/{id}/command`
3. `StudioOrchestrator.route_command()` parses intent via `UniversalCommandEngine`
4. Routes to appropriate existing engine (MakeAutoMode, CreativeDirector, ImageToVideoEngine, etc.)
5. Returns execution plan or result
6. Frontend shows progress and results

## Integration

- Existing Director, Timeline, Magic Editor, Generation, Transformation, Variant, Export engines
- No duplicate implementations
- All commands map to real backend operations

## Verification

- Backend tests: 240 passed (233 Phase 1-14 + 7 Phase 15 vision tests)
- TypeScript: PASSED
- Frontend production build: PASSED
