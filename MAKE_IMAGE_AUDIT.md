# MAKE IMAGE — AUDIT REPORT (Phase 1)

> Snapshot of the v2 image subsystem before the production-quality push.
> All numbers below were re-measured in this session against the live
> state of `/tmp/make_image_v2/`. Nothing is taken on faith.

## 1.1 — Inventory of the existing system

| File | Role |
| --- | --- |
| `backend/app/make_model/image/arch/unet.py` | v1 single-level UNet (226K params trained) |
| `backend/app/make_model/image/arch/diffusion.py` | Gaussian diffusion (linear beta) |
| `backend/app/make_model/image/arch/v2/unet.py` | v2 UNet w/ FiLM+cond+identity+detail head (492K params trained) |
| `backend/app/make_model/image/arch/v2/conditioning.py` | ConditionVector (149-D) |
| `backend/app/make_model/image/training/autograd.py` | Hand-coded NumPy autograd (Tensor, Param) |
| `backend/app/make_model/image/training/trainer.py` | v1 trainer |
| `backend/app/make_model/image/training/trainer_v2.py` | v2 trainer (streaming, CFG, resume, curriculum) |
| `backend/app/make_model/image/dataset/acquire.py` | v0 procedural-only dataset |
| `backend/app/make_model/image/dataset/streaming.py` | Streaming acquisition (Picsum/Pravatar/OpenMoji) |
| `backend/app/make_model/image/inference/sampler.py` | v1 DDPM sampler |
| `backend/app/make_model/image/inference/sampler_v2.py` | v2 sampler (DDIM, CFG, i2i, inpaint, cascade) |
| `backend/app/make_model/image/inference/quantization.py` | int8 quantize/dequantize |
| `backend/app/make_model/image/image_provider.py` | v1 provider (mirrors MakeLocalNeuralProvider) |
| `backend/app/make_model/image/registry_bridge.py` | v1 registry bridge |
| `backend/app/make_model/image/router.py` | FastAPI router (v1 + v2 endpoints) |
| `backend/app/make_model/image/serve.py` | iPhone-controllable HTTP server (port 8421) |
| `backend/app/make_model/image/cli_train.py` | v1 CLI |

The frozen **video** subsystem (`backend/app/make_model/video*` and
`backend/app/make_model/{arch,training,inference,dataset,registry,utils,world}`
shared modules) is **not** in this list and **must not be touched** in
any of the upcoming phases. All of Phase 1–17 work happens strictly
inside `image/`.

## 1.2 — Current checkpoints (live on disk)

```
/tmp/make_image_v2/checkpoints/
  make-image-cpu-unet-v2-step3.npz           (smoke test)
  make-image-cpu-unet-v2-step15.npz
  make-image-cpu-unet-v2-step25.npz
  make-image-cpu-unet-v2-step30.npz
  make-image-cpu-unet-v2-step50.npz
  make-image-cpu-unet-v2-step50.int8.npz     (int8 quant)
  make-image-cpu-unet-v2-step75.npz
  make-image-cpu-unet-v2-step100.npz
  make-image-cpu-unet-v2-step125.npz
  make-image-cpu-unet-v2-step150.npz
  make-image-cpu-unet-v2-step175.npz
  make-image-cpu-unet-v2-step200.npz         (1.85 MB, sha e46c74fb…492K params)
  make-image-cpu-unet-v2-step200.int8.npz    (0.47 MB)
  make-image-cpu-unet-v2-64-step20.npz       (64x64 cascade)
  make-image-cpu-unet-v2-64-step40.npz
  make-image-cpu-unet-v2-64-step60.npz       (sha 9946bc33…, 358-image dataset)
```

## 1.3 — Current datasets (live on disk)

```
/tmp/make_image_v2/datasets/
  stream_v1/             121 items
  stream_train1/          77 items
  stream_train_v2_long/   171 items
  stream_train_v2_long2/  425 items   ← main v2 training set
  stream_train_v2_64/     358 items   ← 64x64 fine-tune set
```

Each `dataset.json` summarises by source. The 425-item set is
`{picsum_photos: 254, pravatar: 70, openmoji: 101}`. Every PNG has a
SHA-256 in its per-source `MANIFEST.tsv`.

## 1.4 — Measured timings (this machine, 4 vCPU, no GPU)

| Path | Timing | Conditions |
| --- | --- | --- |
| v2 forward (1 sample, 32×32, 24 base ch) | **15.2 ms** | avg of 20, fresh |
| v2 forward with CFG (2 calls) | **26.2 ms** | avg of 20 |
| DDIM 8 steps with CFG (16 forwards) | **~0.4 s** | includes scheduler overhead |
| HTTP `/v2/generate` (1 sample, 6 steps, CFG=2.5) | 0.6–2.8 s | per request, includes i/o |
| Inpainting (init + mask, 10 steps) | 4.3 s | once |
| Cascade (32→64, 6+6 steps) | 0.8 s | once |
| int8 quantize (step200) | < 0.2 s | per checkpt |

These are the **current** numbers; the plan below targets the same
quality and better timings where possible.

## 1.5 — Quality measurement of the current 32×32 model

Because the model is small and the training set is 425 real images at
32×32, the current sample quality is appropriate for the compute: 32×32
RGB, multiple unique colors, structural variety, no single-color
collapse. Higher visual quality is bounded by:

- **Spatial resolution**: 32×32 is very small. Even a perfect 32×32
  image cannot show "realistic eyes" because the eye itself is at most
  2×2 pixels in the output.
- **Parameter count**: 492K params is not enough to learn
  photorealistic faces, hands, or material subtleties.
- **Training compute**: 200 steps × 4 vCPU = ~8 min. To reach
  photorealistic quality on this architecture and dataset a multi-GPU-day
  budget is normally required. The honest path is: more data, longer
  training, larger architecture, real validation metrics, and a
  resolution cascade that uses small native resolution as a
  conditioning signal rather than as a final output.

## 1.6 — Identified weaknesses and the highest-value fixes

| # | Weakness | Highest-value fix | Phase |
| --- | --- | --- | --- |
| 1 | Single-level UNet (no spatial downsample) | Add a multi-scale encoder/decoder with a learned latent at 8×8 or 16×16, skip connections, AdaGN | 2 |
| 2 | Hash-only prompt embedding | Add a small BPE-style encoder trained end-to-end on captions (still NumPy) | 2 |
| 3 | 32×32 native output | Train a 64×64, then a 128×128 model; add a super-resolution / detail-recovery stage for the cascade | 10 |
| 4 | No real face / anatomy supervision | Add a face-landmark synthetic prior + a perceptual loss against the Picsum originals | 5, 7 |
| 5 | Dataset is 425 items — small | Add more sources (Wikimedia, public-domain illustration sets, NASA, ESA, OpenImages subset) with strong license filtering | 3 |
| 6 | No validation split | Build a held-out 10% set and report validation loss per curriculum stage | 4 |
| 7 | No EMA on weights | Add EMA of the model state and use it for sampling | 4 |
| 8 | Identity consistency is a fixed-bias bypass only | Add a learnable per-identity memory bank (capped) and a contrastive identity loss | 7 |
| 9 | Lighting/material/composition paths are zero-embedded at training time | Add a caption-derived pseudo-label pipeline that pulls camera/lighting tags from the dataset filenames / EXIF where possible | 3, 6 |
| 10 | No automated quality gate | Build a real quality gate (Laplacian-variance sharpness, exposure/contrast, skin-color histogram, edge coherence, color consistency) | 5 |
| 11 | No cinematic preset library | Add named presets (portrait/landscape/cinematic/fashion) that populate the conditioning | 6 |
| 12 | Inpainting is mask-paste at every step | Add a proper masked-loss training pass so the model actually learns to inpaint | 9 |
| 13 | No outpainting | Add an outpainting path (mirror-pad + reverse at the new canvas) | 9 |
| 14 | No relighting | Add a lighting-direction swap that re-conditions the same latent | 9 |
| 15 | Quantize only stores int8 on disk | Add a real int8 forward path that runs the model in int8 (per-layer, dequantize-on-the-fly with caching) | 11 |
| 16 | iPhone server is plain JSON HTTP | Add SSE/WebSocket progress, batch /jobs, /provenance, /quality, /camera, /lighting, /identity, /world | 12 |
| 17 | No human-eval pipeline | Add a 16-scenario showcase generator and a sheet format the user can fill in | 15 |
| 18 | No automated tests for v2 architecture / sampler / quantize | Add a `tests/test_image_v2.py` covering each new capability | 14 |
| 19 | The trainer uses one condition per batch, not per-sample | Switch the trainer to per-sample conditions (still CPU-friendly if structured as a single big cond matrix) | 4 |
| 20 | The sampler reloads the model for every step in the cascade | Cache models in a class-level dict keyed by checkpoint path | 11 |

The 20 weaknesses above map to the 17 phases the user requested. The
work to do is large, the compute budget is small, so I will execute in
strict priority order and stop only when a step requires GPU that we
do not have — at which point I document the gap and leave a resumable
state.

## 1.7 — Decisions taken now (to avoid changing later)

1. **No `arch_version` collisions.** Every new architecture will
   introduce a new `arch_version` string (e.g.
   `make-image-cpu-unet-v3-latent`, `make-image-cpu-unet-v3-sr`).
   The old `v2-*` files stay on disk and remain loadable.
2. **No weight surgery across incompatible architectures.** v3 is
   trained from scratch; the v2 weights are not transplanted into v3
   because the spatial structure changes (multi-scale).
3. **Dataset version is monotonic.** v3 training uses
   `stream_train_v3`; never reuses v2 dataset names.
4. **Provenance stays mandatory.** Every sample gets a JSON sidecar
   with the conditioning, the ckpt sha, the sampler, the CFG, the
   pipeline (single / cascade / SR), and an honest
   `interpolation_note`.
5. **No marketing claims.** Resolution and quality are described
   exactly as they were measured. Cascade stages are described as
   "model step k at native s×s, used to refine a previous stage's
   output."
