# MAKE World Model X — Architecture

## Decision: spacetime DiT (transformer)

We replaced the previous 3D U-Net baseline with a DiT-style
spacetime transformer. The decision is recorded here as research
discipline: WHY / ALTERNATIVES / TRADEOFFS / BENEFIT / MEASUREMENT.

### Why

- Conv3d scales linearly with depth in receptive field. DiT scales
  with N² in attention but enables global temporal routing from
  layer 1.
- Cross-attention is required for text, image, reference, and motion
  conditioning. DiT has a natural cross-attention slot; 3D U-Net
  does not.
- adaLN-Zero conditioning is an established way to inject
  time + condition into a DiT (Peebles & Xie 2023).
- Patchification decouples memory from frame size in a way conv3d
  does not.

### Alternatives considered

- Pure 3D U-Net (current legacy)
- 3D U-Net + cross-attention at bottleneck (would have worked but
  bottleneck is a bottleneck)
- Diffusion Transformer operating only on spatial tokens (no good
  way to model temporal coherence without explicit time-axis
  attention)
- 3D conv transformer hybrid (we adopted this — DiT with
  spacetime tokens)

### Tradeoffs

- Attention is O(N²) in tokens. For T=8, H=64, P=2 we have N=8*32*32
  = 8192 tokens, which fits in 8GB for SMALL/MEDIUM.
- DiT is data-hungry. We will need ≥1M clips before MEDIUM produces
  reasonable results.
- DiT does not natively do multi-scale; progressive training
  (resolution curriculum) is required.

### Expected benefit

- Global temporal coherence (frame-to-frame routing from layer 1)
- Native cross-attention for text, image, references
- Scalable: TINY → SMALL → MEDIUM → LARGE with the same code path
- Conditioning vector is additive and additive modulation (adaLN) is
  well-understood

### Measurement

- Forward shape: `(B, C, Tt, H, W) -> same` (verified in tests)
- Parameter count: TINY=0.48M, SMALL=2.9M, MEDIUM=69M
- Per-step training time at MEDIUM on a 4090 will be measured on a
  real training host (NOT measured in this phase)

## Components

| Component | File | Purpose |
|---|---|---|
| `MakeWorldModelConfig` | `world/arch.py` | versioned, JSON-serializable |
| `_SpacetimePatchEmbed3D` | `world/arch.py` | (B, C, T, H, W) -> (B, N, D) |
| `_SpacetimePositionalEnc` | `world/arch.py` | 3D (T, H, W) sinusoidal |
| `_AdaLNZero` | `world/arch.py` | adaptive layer norm modulation |
| `_DiTBlock` | `world/arch.py` | self-attn + cross-attn + FFN + adaLN |
| `_MultiHeadAttention` | `world/arch.py` | multi-head QKV attention |
| `_SwiGLU` | `world/arch.py` | SwiGLU FFN |
| `_TimeTextEncoder` | `world/arch.py` | text + time -> c |
| `MakeWorldModelV0` | `world/arch.py` | top-level model |

## Tensor contracts

```
B = batch
T = frames
C = latent channels = 4
H, W = spatial latent dims
P = patch size = 2
Tt = T // temporal_patch (default 1)
Hn, Wn = H // P, W // P
N = Tt * Hn * Wn (token count)
D = hidden dim
S = text sequence length = 16
E = text embedding dim (cfg.text_embed_dim)
R = reference slots = 4
```

Forward:

```
x_noisy: (B, C, Tt, Hn*P, Wn*P)  float32
t:       (B,)                     int64
text_tok:(B, S)                   int64
ref_slots: (B, R, D)              float32 (optional)
first_frame: (B, C, 1, H, W)      float32 (optional)

out: (B, C, Tt, Hn*P, Wn*P)       float32
```

## Conditioning compiler

`ConditioningCompiler.compile(prompt, first_frame, references, camera,
motion, world, seed)` returns a `ConditioningBundle` that bundles:

- `text_tokens`  (deterministic integer tokens, no external tokenizer)
- `cross_ctx`    (resolved inside the model from text_emb)
- `first_frame`  (image conditioning)
- `last_frame`   (image conditioning, optional)
- `ref_slots`    (R x D slots; 4 by default)
- `camera`       (CameraRepresentation)
- `motion`       (MotionRepresentation)
- `world`        (WorldSample)

The compiler does NOT re-implement MAKE's prompt compiler. The
existing `AdvancedPromptCompiler` (in `app/services/`) can be called
to enrich a prompt before passing it to the bundle.

## Denoising loop (research baseline)

Ancestral-style:

```
x_T ~ N(0, I)
for i in [T-1 .. 1]:
    eps = model(x_t, i, text_tok, ...)
    a_t = ab[i]
    a_prev = ab[i-1]
    x0 = (x_t - sqrt(1-a_t) * eps) / sqrt(a_t)
    x_{t-1} = sqrt(a_prev) * x0 + sqrt(1-a_prev) * eps
```

A real production scheduler (DPM-Solver, EDM, etc.) is a future
decision and is not required for the foundation.

## Decoder

The decoder is intentionally minimal for this phase:

```
latent (B, C, Tt, H, W) -> first 3 channels -> mean over C -> (B, Tt, H, W)
  -> normalize 0..1 -> uint8 -> rawvideo pipe to ffmpeg
  -> yuv420p mp4
```

This is NOT a learned decoder. A real production VAE / VAVAE
decoder is a future decision.

## Status

| Capability | Status |
|---|---|
| Architecture implemented | YES |
| Forward pass verified   | YES (tests) |
| Save/load round-trip    | YES (tests) |
| 4 presets               | YES (TINY/SMALL/MEDIUM/LARGE) |
| Cross-attention         | YES |
| Temporal self-attn      | YES (within DiT self-attn) |
| Spatial self-attn       | YES (within DiT self-attn) |
| Reference conditioning  | YES (slots) |
| Image conditioning      | YES (first-frame concat) |
| Resolution curriculum   | CONFIGURED (data engine) |
| Length curriculum       | CONFIGURED (data engine) |
| Long-context training   | NOT TESTED |
| Learned VAE decoder     | NOT IMPLEMENTED |
| Real trained checkpoint | NO |

## Where to read next

- `MAKE_WORLD_MODEL_TRAINING.md`
- `MAKE_WORLD_MODEL_TEMPORAL_LEARNING.md`
- `MAKE_WORLD_MODEL_CONDITIONING.md`
- `MAKE_WORLD_MODEL_SCALING.md`
- `MAKE_WORLD_MODEL_HARDWARE.md`
