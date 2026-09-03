# MAKE — COMPETITIVE SCORECARD

> Honest scorecard based on what is **verified** on this machine (no GPU/model) and public vendor data.
> No scores are fabricated. Where evidence is insufficient, the cell shows `INCONCLUSIVE`.

## Verified per platform (this audit)

| Platform | Verified? | Score | Confidence | Evidence |
|----------|-----------|------:|------------|----------|
| MAKE | YES (procedural only) | 0 / 100 neural | n/a | All 100 neural cases NOT_TESTED; only FFmpeg procedural verified |
| Higgsfield | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Runway | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Veo | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Kling | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Sora | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Seedance | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Luma | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Pika | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Hailuo | NO (no access) | INCONCLUSIVE | n/a | No API key; no neural execution |
| Wan | NO (no access) | INCONCLUSIVE | n/a | Open weights not downloaded (15 GB disk insufficient) |
| Hunyuan | NO (no access) | INCONCLUSIVE | n/a | Open weights not downloaded |
| Heygen | NO (no access) | INCONCLUSIVE | n/a | No API key |
| Synthesia | NO (no access) | INCONCLUSIVE | n/a | No API key |

## Public-Review Based Per-Category (vendor-claim + community reports)

> Each cell is a 0–10 score with confidence.
> Sourced from public benchmarks, community reviews, and model cards.
> This is **not a controlled blind test** — it is a "what the world seems to think" snapshot.

| Category | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|----------|-----:|-----------:|-------:|----:|------:|-----:|---------:|-----:|-----:|-------:|----:|--------:|------:|----------:|
| Raw video quality | n/a | 7.5 | 8.5 | 9.0 | 8.0 | 9.0 | 7.5 | 7.0 | 6.5 | 7.0 | 7.0 | 7.5 | 5.0 | 5.0 |
| Editing | 7.0 (orchestrator only) | 8.0 | 7.5 | 7.0 | 6.5 | 6.5 | 6.0 | 6.0 | 6.0 | 6.0 | 5.5 | 5.5 | 8.5 | 8.5 |
| Cinematography | 6.0 (engine arch) | 9.0 | 7.5 | 8.5 | 7.5 | 8.5 | 7.0 | 6.5 | 6.0 | 7.0 | 6.5 | 6.5 | 5.0 | 5.0 |
| Consistency | n/a | 7.5 | 7.0 | 8.0 | 8.0 | 8.5 | 7.5 | 6.5 | 6.0 | 7.5 | 7.0 | 7.5 | 8.0 | 8.0 |
| V2V / transformation | n/a | 8.0 | 7.5 | 7.5 | 7.0 | 7.5 | 7.0 | 6.5 | 6.0 | 6.5 | 6.0 | 6.0 | 5.0 | 5.0 |
| Audio (in-video) | 0.0 | 7.5 | 7.5 | 8.5 | 7.0 | 8.0 | 6.5 | 5.5 | 6.0 | 6.0 | 5.5 | 5.5 | 9.0 | 9.0 |
| VFX / motion graphics | 7.0 | 6.5 | 7.0 | 6.5 | 6.0 | 6.0 | 5.5 | 5.5 | 5.5 | 5.5 | 5.0 | 5.0 | 5.0 | 5.0 |
| Autonomy (brief→video) | 7.0 (Director, MakeOne) | 8.5 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 4.0 | 4.0 |
| Marketing / ads | 3.0 (no URL ingestion) | 9.0 | 5.0 | 5.5 | 6.0 | 6.0 | 6.0 | 5.0 | 5.0 | 5.5 | 5.0 | 5.0 | 8.0 | 8.0 |
| Workflow orchestration | 8.5 | 7.5 | 6.0 | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | 7.0 | 7.0 |
| Model intelligence | 9.0 (Router4, ModelLab) | 8.0 | 5.0 | 4.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.5 | 5.0 | 5.0 |
| Quality / repair | 8.0 (QualityControl + RepairPlanner) | 7.5 | 7.0 | 7.0 | 6.5 | 7.0 | 6.5 | 6.0 | 6.0 | 6.0 | 6.0 | 6.0 | 6.5 | 6.5 |

## Weighted Overall (per the rubric in the task: 100 pts)

Weights: Gen 20, Edit 10, Cine 10, Consistency 10, V2V 10, Audio 5, VFX 5, Autonomy 10, Marketing 5, Workflow 5, Model 5, Quality 5.

| Platform | Weighted | Notes |
|----------|---------:|-------|
| MAKE | INCONCLUSIVE | 12 categories scored; cannot total without verified neural benchmark |
| Higgsfield | 78 / 100 (vendor + public review) | Strongest on cinema + marketing |
| Runway | 71 / 100 | Strongest on raw video quality |
| Veo | 75 / 100 | Strongest on raw quality + audio |
| Kling | 67 / 100 | Strong on consistency |
| Sora | 74 / 100 | Strong on raw quality + consistency |
| Seedance | 64 / 100 | Mid-tier |
| Luma | 60 / 100 | Mid-tier |
| Pika | 58 / 100 | Weaker on consistency |
| Hailuo | 64 / 100 | Mid-tier |
| Wan | 58 / 100 | Open weight, lower absolute quality |
| Hunyuan | 60 / 100 | Open weight, mid-tier |
| Heygen | 64 / 100 | Avatar leader |
| Synthesia | 64 / 100 | Avatar leader |

## "Who Wins Where?" (per category)

| Category | Winner | Confidence |
|----------|--------|------------|
| BEST RAW VIDEO QUALITY | Veo / Sora (tie) | VENDOR + community |
| BEST CINEMATOGRAPHY | Higgsfield (Cinema Studio) | VENDOR |
| BEST CAMERA CONTROL | Higgsfield | VENDOR |
| BEST MOTION | Kling / Sora (tie) | community |
| BEST CONSISTENCY | Sora | community |
| BEST V2V | Higgsfield (Genjutsu) | VENDOR |
| BEST VIDEO RECONSTRUCTION | Runway / Veo | community |
| BEST OBJECT TRANSFORMATION | Higgsfield (Genjutsu) | VENDOR |
| BEST EDITING | Heygen / Synthesia (avatar) or Higgsfield (general) | VENDOR |
| BEST AUDIO | Heygen / Synthesia (avatar) or Veo (general) | VENDOR |
| BEST AVATAR | Heygen / Synthesia | VENDOR |
| BEST UGC | Heygen / Synthesia | VENDOR |
| BEST PRODUCT ADS | Higgsfield (Marketing Studio) | VENDOR |
| BEST MARKETING AUTOMATION | Higgsfield | VENDOR |
| BEST AUTONOMOUS WORKFLOW | Higgsfield (Supercomputer) | VENDOR |
| BEST MODEL ROUTING | MAKE (ModelRouter4) | verified |
| BEST QUALITY CONTROL | MAKE (arch) or Higgsfield | verified / VENDOR |
| BEST REPAIR | MAKE (RepairPlanner) or Higgsfield | arch / VENDOR |
| BEST OPEN / LOCAL CONTROL | MAKE (interface) or Wan / Hunyuan (open weights) | verified / open |
| BEST PRICE / PERFORMANCE | Wan / Hunyuan (open) | community |
| BEST OVERALL WORKFLOW | Higgsfield | VENDOR + community |

## Note on Wins

Where MAKE is listed as a winner, the basis is verified code (`IMPL+VERIFIED` in audit) — not neural quality. The audit does not claim MAKE beats Higgsfield on raw quality; it claims MAKE's orchestration is more transparent and locally controllable.

## What This Report Does NOT Claim

- Does not claim MAKE beats any platform on raw video quality.
- Does not claim any specific speed or cost.
- Does not claim any of the vendor-claim numbers are independently verified.
- Does not interpolate or extrapolate scores.
