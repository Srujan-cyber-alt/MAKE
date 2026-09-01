# MAKE QUALITY SYSTEM

## Validation Pipeline

Every generated shot passes through:

1. **Technical Validation** — FFprobe inspects: duration, resolution, FPS, codec, file size
2. **Temporal Consistency** — Flicker detection, frame-to-frame coherence
3. **Identity Consistency** — Face/person/product preservation checks
4. **Motion Quality** — Physical plausibility, smoothness
5. **Composition** — Framing, rule of thirds, balance
6. **Audio Quality** — Loudness, clarity, sync

## Scoring

Each check contributes to an overall quality score (0.0–1.0).

Thresholds:
- **0.9+**: Cinematic quality
- **0.8+**: Commercial quality
- **0.7+**: Acceptable
- **<0.7**: Requires repair

## Auto Repair

If score < threshold:
1. Diagnose issue type
2. Select repair strategy
3. Regenerate with modified prompt/model/parameters
4. Revalidate
5. Keep best result

## Result Validator

`ResultValidator` checks:
- File exists and is readable
- Duration > 0
- Resolution >= 256x256
- FPS > 0
- File size > 1KB

Warnings for:
- Duration off by >50%
- Resolution off by >30%
- FPS outside 1–120
- File size < 1KB

## Verification

- FFprobe validation tested
- Export validation tested
- Quality control tested
