# MAKE World Model X — Data Engine

Lives at `backend/app/make_model/world/data_engine.py`.

## What it does

1. **Ingestion.** Walks a directory of video files. For each file:
   - computes SHA-256
   - runs ffprobe for width / height / fps / nb_frames
   - decodes 8 frames at 64x64 for quality scoring
2. **Validation.** Rejects files that:
   - are corrupted (decode fails)
   - have invalid dimensions or fps
   - have fewer than `min_frames` frames
3. **Quality scoring.** Per clip:
   - sharpness (sobel-like)
   - brightness, contrast, saturation
   - motion (mean luma diff between frames)
   - black_frame_ratio, frozen_frame_ratio
   - aesthetic placeholder (real aesthetic head lives in MAKE's
     existing systems)
4. **Dedup.**
   - exact-hash: skip duplicate SHA-256
   - perceptual: 8x8 aHash + Hamming distance ≤ threshold
5. **Clip writing.** FFmpeg re-encode to a fixed short-side, fps,
   and frame count (defaults 64, 8, 8).
6. **Caption.** Reads a sidecar `.txt` / `.caption` / `.json` next
   to the source file (optional).
7. **License.** Records a `SourceLicense` per sample.
8. **Split.** Deterministic split (train/val/test) by sample id.
9. **Manifest.** Writes `manifest.json` (full samples) and
   `skipped.json` (rejection reasons).

## Why

Training a generative video model from raw "videos" is a fool's
errand. The data must be:

- deduplicated (perceptual, not just exact)
- quality-scored
- license-recorded
- deterministically split
- reproducibly versioned

This module is the foundation for all of that.

## What is NOT in the engine

- No downloaders, no scrapers, no network calls
- No automatic captioning model (the existing vision system can
  be plugged in later)
- No aesthetic head (aesthetic_score is a placeholder; the real
  system runs a frozen CLIP aesthetic head)
- No face / product / identity segmentation (those are the job of
  the existing IdentityEngine / ProductSystem)

## Data record

Each `TrainingSample` carries:

```json
{
  "sample_id": "0000001234-000001",
  "source_path": "/abs/path/src.mp4",
  "source_sha256": "...",
  "source_bytes": 12345,
  "clip_path": "clips/0000001234-000001.mp4",
  "clip_sha256": "...",
  "clip_bytes": 6789,
  "width": 64, "height": 64,
  "frames": 8, "fps": 8.0,
  "duration_seconds": 1.0,
  "caption": "...",
  "quality": {
    "sharpness": 0.18, "brightness": 0.5, "contrast": 0.6,
    "saturation": 0.4, "motion": 0.07,
    "black_frame_ratio": 0.0, "frozen_frame_ratio": 0.0,
    "aesthetic_score": 0.0
  },
  "license": {
    "source": "user_supplied",
    "license": "unknown",
    "permission_status": "unknown",
    "acquisition_method": "local",
    "notes": ""
  },
  "motion_metadata": {"motion_score": 0.07, "scene_change_count": 0},
  "camera_metadata": {},
  "subject_metadata": {},
  "scene_metadata": {"scenes": []},
  "split": "train",
  "dataset_version": "0.1.0"
}
```

## License rejection

A future training step will refuse to ingest datasets whose
`SourceLicense.permission_status` is `unknown`. The infrastructure
exists; the enforcement is opt-in via the training config.

## Resolution / length curriculum

The data engine emits fixed-size clips (default 64x64x8). The
`DataEngineConfig` controls:

- `target_short_side`
- `target_frames`
- `target_fps`

Changing these between training stages produces a resolution /
length curriculum without re-ingesting source data (because the
source SHA-256 is preserved on the manifest).

## Status

| Capability | Status |
|---|---|
| Local ingest            | YES |
| ffprobe metadata        | YES |
| Quality scoring         | YES (heuristic) |
| Dedup (exact)           | YES |
| Dedup (perceptual)      | YES (aHash) |
| Manifest IO             | YES (JSON) |
| License recording       | YES |
| Deterministic split     | YES |
| Scene detection         | YES (luma diff threshold) |
| Auto-captioning         | NOT IMPLEMENTED (placeholder) |
| Aesthetic scoring       | NOT IMPLEMENTED (placeholder) |
| Subject segmentation    | NOT IMPLEMENTED (uses existing systems) |
| Resolution curriculum   | CONFIGURED |
| Length curriculum       | CONFIGURED |
| Network ingest          | NOT IMPLEMENTED (local only) |

## Where to read next

- `MAKE_WORLD_MODEL_TRAINING.md`
- `MAKE_WORLD_MODEL_TEMPORAL_LEARNING.md`
- `MAKE_WORLD_MODEL_PROVENANCE.md`
