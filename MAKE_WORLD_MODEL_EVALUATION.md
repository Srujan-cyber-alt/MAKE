# MAKE World Model X — Evaluation

Lives at `backend/app/make_model/world/evaluation.py`.

## Prompt set

`EVALUATION_PROMPTS` ships **105 carefully designed prompts** across
**20 categories**:

  basic_motion, complex_motion, humans, animals, vehicles, products,
  environments, camera_control, lighting, weather, interactions,
  identity, product_fidelity, long_temporal, difficult_prompts,
  compositional, cinematic, physics, reference, adversarial

Same prompts, same references, same resolution, same duration,
same evaluation criteria.

## Harness

`EvaluationHarness(engine).run(prompts, model_name, seed, frames,
short_side, fps, steps)` produces an `EvaluationSummary`:

```json
{
  "total": 105,
  "passed": 0,
  "failed": 0,
  "blocked": 105,
  "elapsed_seconds": 4.2,
  "by_category": {
    "basic_motion": {"total": 5, "ok": 0, "failed": 0, "blocked": 5},
    ...
  },
  "rows": [ ... 105 rows ... ]
}
```

When no checkpoint exists, every prompt is `blocked` with
`code="MAKE_MODEL_X_UNTRAINED"`. The harness will not report a
single "passed" until a real trained checkpoint produces a real
video for that prompt.

## Why competitor benchmarks are NOT run

We do not run competitor benchmarks until a real MAKE inference
produces real video frames. The 100-prompt set is the same for
MAKE and any future competitor. The resolution, duration, fps,
seed, and conditioning are identical.

## Validation hooks for future versions

`ValidationSummary` is the input to MAKE's existing quality
systems. The future versions will call:

- text adherence      — CLIP score (existing infrastructure)
- temporal consistency — MAKE Continuity
- motion quality       — MAKE Vision Engine
- camera adherence     — MAKE CameraControlEngine
- identity             — MAKE IdentityEngine
- product              — MAKE ProductSystem
- world                — MAKE WorldSystem
- composition          — MAKE Composition Engine
- visual quality       — MAKE Quality
- artifact rate        — MAKE ArtifactDetector

No new quality engine is built.

## Status

| Capability | Status |
|---|---|
| 100+ prompts (20 cats)  | YES (105 prompts) |
| Same input convention   | YES |
| Harness that refuses if untrained | YES |
| Per-category summary    | YES |
| Per-prompt row          | YES |
| **Real evaluation**     | **NO (no checkpoint)** |
| **Competitor benchmarks** | **NOT RUN** |

## Where to read next

- `MAKE_WORLD_MODEL_HARDWARE.md`
- `MAKE_WORLD_MODEL_REALITY_REPORT.md`
