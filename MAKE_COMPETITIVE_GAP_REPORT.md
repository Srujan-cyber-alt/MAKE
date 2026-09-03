# MAKE — COMPETITIVE GAP REPORT

> Each gap lists the competitor capability, why it matters, MAKE's current state, the implementation difficulty, the impact, and a priority (P0–P3).

## P0 — Critical (blocks competitive relevance)

### G1. Real local neural video generation
- **Competitor**: Runway, Veo, Sora, Kling, Seedance, Luma, Pika, Hailuo, Wan, Hunyuan, Higgsfield
- **Why it matters**: Without real neural inference, MAKE cannot win any generation category.
- **Current MAKE state**: `ARCH-ONLY` / `IMPL+HW-DEP`; `LocalNeuralProvider` interface defined, no model loaded, no GPU on this machine.
- **Difficulty**: HIGH (requires GPU, model weights, runtime install)
- **Impact**: HIGH
- **Priority**: **P0**
- **Fix**: install GPU + PyTorch + diffusers + LTX-Video 2B (or similar); wire `LocalNeuralProvider`; re-run benchmark.

### G2. Real local neural I2V
- **Competitor**: Runway, Veo, Sora, Kling, SVD, Wan, Hunyuan
- **Why it matters**: Image-to-video is the highest-demand AI video workflow in 2026.
- **Current MAKE state**: `IMPL+HW-DEP`
- **Difficulty**: HIGH (model-specific adapter)
- **Impact**: HIGH
- **Priority**: **P0**

### G3. Native in-video audio (music, SFX, voice)
- **Competitor**: Veo, Sora, Hailuo, Runway, Heygen, Synthesia
- **Why it matters**: Audio is now a first-class citizen; without it, MAKE videos feel half-finished.
- **Current MAKE state**: `NO`; FFmpeg pipeline can mux but cannot generate
- **Difficulty**: MEDIUM (model-DEP + provider integration)
- **Impact**: HIGH
- **Priority**: **P0**

### G4. Lip sync / dialogue
- **Competitor**: Heygen, Synthesia, Sora, Veo, Runway
- **Why it matters**: UGC / avatar / talking-head content requires it.
- **Current MAKE state**: `NO`; arch slot exists in audio system
- **Difficulty**: MEDIUM
- **Impact**: HIGH
- **Priority**: **P0**

### G5. Real product consistency (neural)
- **Competitor**: Higgsfield, Runway, Veo, Sora, Kling
- **Why it matters**: Product advertising is the highest-value commercial use case.
- **Current MAKE state**: `ARCH-ONLY`; `product_consistency.py` has logic but no real model
- **Difficulty**: HIGH (model + adapter)
- **Impact**: HIGH
- **Priority**: **P0**

## P1 — Major (significant competitive gap)

### G6. Real character consistency (neural)
- **Competitor**: Higgsfield (Elements), Runway, Veo, Sora, Kling
- **Why it matters**: Long-form storytelling requires persistent character identity.
- **Current MAKE state**: `ARCH-ONLY`; `character_system.py` has logic, no real model
- **Difficulty**: HIGH
- **Impact**: HIGH
- **Priority**: **P1**

### G7. Product URL → Ad
- **Competitor**: Higgsfield (Marketing Studio)
- **Why it matters**: Lowest-friction ad production flow.
- **Current MAKE state**: `NO`; no URL ingestion
- **Difficulty**: MEDIUM (scrape + analyze + plan)
- **Impact**: HIGH
- **Priority**: **P1**

### G8. Real motion transfer
- **Competitor**: Runway, Higgsfield, Wan
- **Why it matters**: Many creative use cases require transferring motion from a reference video.
- **Current MAKE state**: `IMPL+HW-DEP`; `motion_transfer_service.py` exists
- **Difficulty**: HIGH
- **Impact**: MEDIUM
- **Priority**: **P1**

### G9. Real V2V / video reconstruction
- **Competitor**: Runway, Veo, Sora, Higgsfield (Genjutsu)
- **Why it matters**: Edit existing footage, restyle, enhance.
- **Current MAKE state**: `IMPL+HW-DEP`; `v2v_engine.py` and `video_to_video_engine.py` exist
- **Difficulty**: HIGH
- **Impact**: HIGH
- **Priority**: **P1**

### G10. Real video extension
- **Competitor**: Runway, Veo, Sora
- **Why it matters**: Extend shots to longer durations without regeneration.
- **Current MAKE state**: `IMPL+HW-DEP`; `video_extension_engine.py` exists
- **Difficulty**: HIGH
- **Impact**: MEDIUM
- **Priority**: **P1**

### G11. Real object swap / replacement
- **Competitor**: Higgsfield (Genjutsu), Runway
- **Why it matters**: Product placement, character swap, prop replacement.
- **Current MAKE state**: `IMPL+HW-DEP`; `transformation_engine.py` orchestrates
- **Difficulty**: HIGH
- **Impact**: MEDIUM
- **Priority**: **P1**

### G12. Real avatar / talking head
- **Competitor**: Heygen, Synthesia
- **Why it matters**: UGC and corporate content depend on it.
- **Current MAKE state**: `NO`; no avatar pipeline
- **Difficulty**: MEDIUM (model + adapter)
- **Impact**: MEDIUM
- **Priority**: **P1**

## P2 — Useful (improves competitive parity)

### G13. Real music generation
- **Competitor**: Suno, Udio, plus in-video from Veo/Sora
- **Why it matters**: Soundtrack matters for ads.
- **Current MAKE state**: `NO`
- **Difficulty**: MEDIUM (provider integration)
- **Impact**: MEDIUM
- **Priority**: **P2**

### G14. Real voice / TTS
- **Competitor**: ElevenLabs, OpenAI, plus in-video from Veo/Sora
- **Why it matters**: Narration, dubbing, voice cloning.
- **Current MAKE state**: `PROV-DEP` (no provider integrated yet)
- **Difficulty**: LOW (integrate existing TTS API)
- **Impact**: MEDIUM
- **Priority**: **P2**

### G15. Real camera control with neural model
- **Competitor**: Higgsfield (Cinema Studio), Runway
- **Why it matters**: Cinematic moves are the bread-and-butter of premium content.
- **Current MAKE state**: `IMPL+PROV-DEP`
- **Difficulty**: MEDIUM
- **Impact**: MEDIUM
- **Priority**: **P2**

### G16. Real keyframe control
- **Competitor**: Runway, Veo, Sora, Kling
- **Why it matters**: Director-style precise control.
- **Current MAKE state**: `IMPL+HW-DEP`
- **Difficulty**: HIGH
- **Impact**: MEDIUM
- **Priority**: **P2**

### G17. Real UGC generation
- **Competitor**: Higgsfield, Heygen, Synthesia
- **Why it matters**: Short-form UGC is a fast-growing use case.
- **Current MAKE state**: `HW-DEP`
- **Difficulty**: HIGH
- **Impact**: MEDIUM
- **Priority**: **P2**

### G18. Real batch / variant generation at scale
- **Competitor**: Higgsfield, Runway, Veo
- **Why it matters**: A/B testing requires many variants.
- **Current MAKE state**: `IMPL+VERIFIED` orchestrator; no real neural backend to scale
- **Difficulty**: MEDIUM
- **Impact**: MEDIUM
- **Priority**: **P2**

### G19. Real prompt adherence benchmark
- **Why it matters**: Without GPU we cannot run our own benchmark.
- **Current MAKE state**: `IMPL+VERIFIED` (orchestrator) but no neural execution
- **Difficulty**: HIGH (model + GPU)
- **Impact**: HIGH
- **Priority**: **P2**

## P3 — Optional (differentiation polish)

### G20. Real-time collaborative editing
- **Competitor**: Frame.io, Adobe Frame
- **Current MAKE state**: `NO`
- **Priority**: P3

### G21. MCP / CLI / API for external agents
- **Competitor**: Runway API, Veo API
- **Current MAKE state**: `IMPL+VERIFIED` (FastAPI), no MCP server
- **Priority**: P3

### G22. Real-time preview / streaming
- **Current MAKE state**: `IMPL+VERIFIED` (real-time progress)
- **Priority**: P3

### G23. Node-based workflow editor
- **Competitor**: ComfyUI, Runway Workflows
- **Current MAKE state**: `NO`
- **Priority**: P3

## Implementation Priority Order

1. **G1 + G2** (neural video + I2V) — the foundation. Without it, MAKE cannot be competitive.
2. **G3 + G4** (audio + lip sync) — biggest UX gap.
3. **G5 + G6** (product + character consistency) — the moat for ads and stories.
4. **G7** (URL → ad) — marketing wedge.
5. **G8–G12** (V2V, extension, swap, motion transfer, avatar) — workflow completeness.
6. **G13–G19** — depth and polish.
7. **G20–G23** — differentiators.
