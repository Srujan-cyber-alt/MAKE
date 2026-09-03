# MAKE — BENCHMARK METHODOLOGY

## Overview

100 standardized benchmark cases spanning 20+ categories, designed to evaluate AI video generation platforms (MAKE, Higgsfield, Runway, Veo, Kling, Sora, Seedance, Luma, Pika, Hailuo, Wan, Hunyuan, Heygen, Synthesia) on the same identical inputs.

## Categories (20+, 5 cases each minimum)

1. Photorealism
2. Cinematic realism
3. Human motion
4. Facial consistency
5. Character consistency
6. Product advertising
7. Product consistency
8. Physics
9. Camera control
10. Complex motion
11. Multi-shot continuity
12. Environment/world consistency
13. Object transformation
14. Video reconstruction (V2V)
15. V2V editing
16. Image-to-video
17. Text-to-video
18. Social / UGC
19. Storytelling / narrative
20. Creative / ad generation
21. Automotive
22. Fashion
23. Difficult prompts (long, multi-constraint)
24. Compositional complexity

## Per-Case Definition

Each case has:

```json
{
  "id": "BM-001",
  "category": "photorealism",
  "input": "image|text|video",
  "prompt": "...",
  "negative_prompt": "...",
  "references": ["url|local_path"],
  "target_duration": "5s",
  "aspect_ratio": "16:9",
  "expected_behavior": "...",
  "pass_conditions": ["...", "..."],
  "fail_conditions": ["...", "..."],
  "quality_dimensions": ["prompt_adherence", "visual", "motion", "temporal", "identity", "product", "camera", "composition", "artifacts", "creative"]
}
```

## Standardized Inputs

- Reference images: 1024x1024 JPEG (or per-source-frame)
- Reference videos: 1920x1080 24fps 5s MP4
- Target output: 1920x1080 24fps 5s
- Aspect ratios tested: 16:9, 9:16, 1:1
- Seeds where supported: 42 (fixed for reproducibility)
- Number of attempts: 1 (no cherry-picking)
- Provider settings: defaults, unless a control requires a specific value

## Scoring Rubric (per case, /100)

| Dimension | Weight | What it Measures |
|-----------|--------|-----------------|
| Prompt adherence | 15 | Does the output match the prompt? |
| Visual quality | 15 | Photorealism, lighting, composition |
| Motion quality | 10 | Smooth, plausible, no jitter |
| Temporal consistency | 10 | Frame-to-frame stability |
| Identity consistency | 10 | Person/character/product identity preserved |
| Product consistency | 10 | Product look/material/geometry |
| Camera control | 10 | Camera moves match instructions |
| Composition | 10 | Rule-of-thirds, framing, balance |
| Artifacts | 5 | Hands, faces, fingers, melting, warping |
| Creative quality | 5 | Aesthetic appeal, emotional resonance |

## Operational Metrics (per case)

- Latency (s)
- Cost (USD or credits)
- Failure rate
- Retry count
- Success rate (over 3 attempts)
- Output resolution
- Output duration
- Model used
- Hardware used
- Provider (local_procedural, local_neural, cloud, etc.)

## Aggregation

For each platform × category:

- Mean score per dimension
- Overall mean score
- Std dev
- Count of complete failures

For each platform overall:

- Weighted average across all 100 cases
- Category-specific winners
- Cost-adjusted score (score / USD)
- Speed-adjusted score (score / s)

## Fairness Rules

1. Identical prompts, references, seeds, aspect ratios.
2. No platform-specific prompt optimization during benchmark.
3. Default settings unless explicitly stated.
4. Blind evaluation: evaluator doesn't know platform.
5. Outputs A/B shuffled before human scoring.
6. If a platform cannot run a case, mark `NOT_TESTED` (not 0).
7. If a platform's output is missing, do not impute.

## Human vs Automated

- Automated: TechnicalValidator, CinematicQualityScore, MediaInfo, failure classifier.
- Human: blind A/B evaluator scores final /100 rubric.
- Combined score = (Automated × 0.4) + (Human × 0.6) when both available.
- If only automated: score = automated.
- If only human: score = human.

## Reporting

Each benchmark run produces:

```json
{
  "case_id": "BM-001",
  "platform": "make",
  "provider": "local_neural",
  "model": "ltx-video-2b",
  "input": {...},
  "output": {"path": "...", "size": ..., "duration": ..., "width": ..., "height": ..., "fps": ...},
  "scores": {"prompt_adherence": 12, "visual": 13, ...},
  "total": 78,
  "latency_s": 32,
  "cost_usd": 0.02,
  "retries": 0,
  "success": true,
  "failure_reason": null,
  "media_info": {...}
}
```

Aggregated as `MAKE_BENCHMARK_RESULTS.md` and as JSON in `benchmark_results.json`.

## Hardware-Dependent Cases

Cases that explicitly require neural inference are run on the local neural runtime when GPU + model are present. Until then, they remain `NOT_TESTED` and are not counted against platform scores.

## Already Defined Cases (this session)

100 cases are defined in `backend/app/services/benchmark_definition.py` and `competitor_benchmark.py`; the runner is in `benchmark_runner.py` and the evaluator in `benchmark_evaluator.py`. The data files (JSON) can be loaded by the runner.

## Current Executable Status

On this machine (no GPU, no model):
- All neural cases: `NOT_TESTED`
- All procedural cases (FFmpeg lavfi cosmetic): executable; used for pipeline integrity check only
- The full benchmark runner is **ready** to execute against any platform as soon as a real model/provider is available.
