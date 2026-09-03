# MAKE — COMPETITIVE FEATURE MATRIX

> Comparison of MAKE against the world's leading AI video platforms.
> Sources cited are public, dated 2026-09-03 where possible. Vendor marketing is marked `VENDOR CLAIM`; independent verification is `THIRD-PARTY`. Where this audit cannot run a neural test, the cell shows `HW-DEP` or `PROV-DEP`.
> **MAKE column reflects the actual code, not documentation.**

## Legend

- `YES` — verified, code shipped and tested
- `PARTIAL` — implemented, gaps remain
- `NO` — not implemented
- `UNKNOWN` — public info insufficient
- `HW-DEP` — needs GPU/model (not available here)
- `PROV-DEP` — needs cloud provider API key
- `VENDOR` — vendor claim, not independently verified
- `ARCH-ONLY` — contract/interface exists, no real engine

## Generation

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Text → Video | `HW-DEP` (FFmpeg procedural alt) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO (avatar-led) |
| Image → Video | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Video → Video | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Video extension | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Video reconstruction | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Object swap | `HW-DEP` | YES (Genjutsu, VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Object removal | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Background replace | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Motion transfer | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Character consistency | `ARCH-ONLY` (no real model) | YES (Elements, VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (avatar, VENDOR) | YES (avatar, VENDOR) |
| Product consistency | `ARCH-ONLY` (no real model) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| World consistency | `ARCH-ONLY` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |

## Cinematography & Camera

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Camera control (lens, focal, aperture) | `PROV-DEP` | YES (Cinema Studio, VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Multi-shot | YES (Director, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Shot continuity | YES (ContinuityEngine, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Keyframes | `HW-DEP` (orchestrator works) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| References (image/video) | YES (ReferenceIntelligence, IMPL+VERIFIED) | YES (Elements, VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |

## Audio

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Native audio (in generated video) | `NO` (no model supports it) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Voice / TTS | `PROV-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Lip sync | `NO` (arch only) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| SFX | `NO` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Music | `NO` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| AV sync | PARTIAL (FFmpeg align) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |

## Editing

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Natural language editing | YES (UniversalCommandEngine) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Timeline editing | YES (TimelineService, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Object replace | `HW-DEP` | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Mask / Track | YES (FFmpeg + trackers, IMPL+VERIFIED arch) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Color | YES (ColorLookEngine) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| VFX | YES (VFXEngine, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Motion graphics | YES (IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Captions | YES (IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Upscale | YES (FFmpeg `scale`; neural = HW-DEP) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | NO | NO |
| Retime | YES (FFmpeg setpts) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |

## Autonomy & Marketing

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| AI Director (brief → video) | YES (Director, IMPL+VERIFIED) | YES (Supercomputer, VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | NO | NO |
| Autonomous agent | YES (MakeAutoMode, MakeOne, IMPL+VERIFIED) | YES (VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| Product URL → Ad | NO (no URL ingestion) | YES (Marketing Studio, VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| UGC | `HW-DEP` | YES (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | PARTIAL (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Marketing Studio | PARTIAL (MakeOne, but no URL ingestion) | YES (VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | PARTIAL | PARTIAL |
| Batch / variations | YES (VariantEngine, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Templates | YES (ProductionTemplates) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Social versions | YES (SocialExport) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |

## Model Intelligence

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Model routing | YES (ModelRouter4, IMPL+VERIFIED) | YES (VENDOR) | NO (single model) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| Model ensemble | YES (ParallelGeneration, IMPL+VERIFIED) | YES (VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| Model comparison | YES (ModelComparison, IMPL+VERIFIED) | YES (VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| Model leaderboard | YES (ModelLeaderboard) | YES (VENDOR) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| Cost control | YES (BudgetController, CostEngine) | PARTIAL (VENDOR) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

## Quality & Reliability

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Quality control | YES (QualityControl, IMPL+VERIFIED) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Auto repair | YES (RepairPlanner) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | UNKNOWN | UNKNOWN |
| Best result selection | YES (BestResultSelector) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Failure recovery | YES (FailureIntelligence) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) | YES (VENDOR) |
| Provenance | YES (ProvenanceTracker, IMPL+VERIFIED) | PARTIAL (VENDOR) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Cancellation / retry | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES |

## Local / Open

| Capability | MAKE | Higgsfield | Runway | Veo | Kling | Sora | Seedance | Luma | Pika | Hailuo | Wan | Hunyuan | Heygen | Synthesia |
|------------|------|-----------|--------|-----|-------|------|----------|------|------|--------|-----|---------|--------|-----------|
| Local neural possible | YES (interface ready, needs GPU) | NO (cloud only) | NO | NO | NO | NO | NO | NO | NO | PARTIAL (open weights) | YES (open) | YES (open) | NO | NO |
| Local-first architecture | YES (LOCAL_ONLY default) | NO | NO | NO | NO | NO | NO | NO | NO | PARTIAL | YES | YES | NO | NO |
| LOCAL_ONLY enforcement | YES (16 dedicated tests) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |

## Summary Observations

- **MAKE** has strong workflow/orchestration coverage (Director, MakeOne, ContinuityEngine, ModelRouter4, ModelLab) but lacks any executed neural generation on this machine.
- **Higgsfield** leads on marketing/UGC breadth (Marketing Studio, Genjutsu) but is cloud-only.
- **Runway** is the long-standing benchmark for raw model quality but is single-model and cloud-only.
- **Veo / Sora** are strongest in raw cinematic quality and long-context understanding.
- **Kling / Seedance / Hailuo / Wan / Hunyuan** are strong on motion and identity consistency.
- **Luma / Pika** are strong on Dream Machine-style I2V.
- **Heygen / Synthesia** are avatar-led UGC specialists.

## Confidence

- MAKE: **HIGH** (verified against code, unit tests, live API)
- Higgsfield/Runway/Veo/Kling/Sora/Seedance/Luma/Pika/Hailuo/Wan/Hunyuan: **MEDIUM** (vendor claims + public reviews)
- Heygen/Synthesia: **HIGH** for avatar domain (well-known)

## Sources

- Higgsfield product pages (cinema studio, supercomputer, marketing studio, genjutsu, elements, ai director)
- Runway Gen-4 product pages
- Google Veo 3 product page
- OpenAI Sora product page
- Kling AI product page
- ByteDance Seedance product page
- Luma Dream Machine page
- Pika product page
- Hailuo/MiniMax product page
- Wan 2.1 / HunyuanVideo model cards on Hugging Face
- Heygen / Synthesia product pages

All sources are public product pages, model cards, or community reviews. Where the public info is silent, the cell is `UNKNOWN`.
