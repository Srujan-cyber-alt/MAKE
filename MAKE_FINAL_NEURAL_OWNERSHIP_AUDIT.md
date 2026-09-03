# MAKE — Final Neural Model Ownership Audit
# Public Generation E2E Verification
# Proprietary Model Gap Analysis

Audit date: 2026-09-03
Repository: /workspace/9e5e888e-cbcf-427b-8a53-56cdad392c91/sessions/agent_83180342-0af8-4797-86a8-c6baff7a51f2
Auditor: Kilo
Mode: AUDIT FIRST, NO INVENTED FUNCTIONALITY

---

## PART A — CURRENT PUBLIC MAKE STATUS

| Item | Value | Evidence |
|------|-------|----------|
| Public HTTPS URL | https://anytime-telecharger-advantages-antivirus.trycloudflare.com/ | cloudflared output 2026-09-03T11:59:59Z |
| Cloudflare edge | 198.41.192.57 (lhr10) | cloudflared log: `Registered tunnel connection connIndex=0 connection=47c104bb-... location=lhr10 protocol=quic` |
| Tunnel type | Quick Tunnel (no auth, no SLA) | cloudflared banner: "account-less Tunnels have no uptime guarantee" |
| Origin | Vite 0.0.0.0:5173 (proxies /api/* → 127.0.0.1:8000) | `vite --host 0.0.0.0 --port 5173`; verified `GET /api/v1/` → 200 OK |
| Frontend HTTP | 200 (909 bytes) | External `GET /` via tunnel |
| API HTTP | 200 (65 bytes: `{"name":"MAKE AI Video","version":"0.1.0","status":"operational"}`) | External `GET /api/v1/` via tunnel |
| Health | 200 (`{"status":"healthy",...}`) | External `GET /api/v1/health/` via tunnel |
| Auth | Register 201, Login 200, /me 200 | External via tunnel |
| CORS | Pre-flight 204; allow-methods include POST/GET/PATCH/DELETE | External OPTIONS via tunnel |
| CORS_ORIGINS | http://localhost:3000, http://localhost:5173, http://localhost:5174, http://10.0.0.1:5173, http://10.0.0.1:8000, https://anytime-telecharger-advantages-antivirus.trycloudflare.com | `backend/.env` line 16 |
| Cloud providers | All disabled: RUNWAY_API_KEY=_, PIKA_API_KEY=_, REPLICATE_API_TOKEN=_, STABILITY_API_KEY=_ | `backend/.env` lines 11-14 |
| DEFAULT_VIDEO_PROVIDER | local | `backend/.env` line 15 |
| Port 8000 direct exposure | NONE (only via vite proxy) | cloudflared points to localhost:5173 only |
| DB / Redis / shell / secrets | None exposed | Only port 5173 is tunneled |
| LOCAL_ONLY | ENABLED | No third-party cloud API calls anywhere |

---

## PART B — REPOSITORY FORENSIC AUDIT: IS THERE A PROPRIETARY NEURAL VIDEO MODEL?

### B.1 — Model weight files (forensic count)

Forensic `find` across the ENTIRE repository (excluding `.git`, `.venv`, `node_modules`):

```
extensions searched: *.safetensors *.ckpt *.pth *.pt *.gguf *.onnx
                     *.engine *.tflite *.h5 *.pb *.bin *.npy *.npz
files found: 0
```

**Result: ZERO model weight files exist anywhere in the repository.**

The single directory named `models/` at `backend/app/models/` contains only:
- `models.py` (20,311 bytes) — **SQLAlchemy ORM schema** (UserRole, ProjectStatus, AssetType, JobStatus, Job, Asset, Project, …). This is the database schema, NOT a model.

### B.2 — Training infrastructure

| Search | Result |
|--------|--------|
| `train*.py` / `training*.py` / `finetune*.py` / `pretrain*.py` | 0 files |
| `dataset*.py` / `dataloader*.py` / `webvid*` / `ucf101*` | 0 files |
| `class.*\(nn\.Module` / `nn\.Module\)` (neural net classes) | 0 matches |
| `torch.optim`, `AdamW`, `def train_epoch`, `def training_step`, `def fit` | 0 matches |
| `from torch.utils.data`, `DataLoader` | 0 matches |
| `datasets/`, `video_data/`, `checkpoints/`, `weights/`, `pretrained/`, `lora/`, `vae/`, `unet/`, `transformer/`, `denoiser/` directories | 0 directories |

**Result: ZERO training infrastructure. There is no code in the repo capable of training any model.**

### B.3 — Neural architecture references in source

| Search term | Hits | Context |
|-------------|------|---------|
| `diffusion` | 0 | none |
| `DiT` | 0 | none |
| `denoise` | 0 | none |
| `temporal attention` | 0 | none |
| `spatiotemporal` | 0 | none |
| `noise prediction` | 0 | none |
| `latent sampling` | 0 | none |
| `inference pipeline` (neural sense) | 0 | none |
| `3D UNet` | 0 | none |
| `video VAE` | 0 | none |

The only "torch" references in source code are **capability-detection** code that probes whether `torch.cuda.is_available()` would work *if torch were installed*. They never instantiate any model, run any inference, or call any neural-network method.

Verified:

```
$ python3 -c "import torch"
ModuleNotFoundError: No module named 'torch'
```

### B.4 — ML library dependencies

`backend/requirements.txt` (full ML-related search):

```
$ grep -iE "torch|diffusers|transformers|safetensors|onnx|accelerate|comfy|opencv|tensorflow|jax|flax" requirements.txt
(no output — 0 lines match)
```

`backend/.venv` site-packages:

```
$ ls .venv/lib/python3.10/site-packages/ | grep -iE "^(torch|diffusers|transformers|safetensors|onnx|accelerate|comfy|huggingface)"
(no output)
```

**Result: ZERO ML libraries installed or pinned.** No torch, no diffusers, no transformers, no safetensors, no onnx, no accelerate, no comfy, no opencv. No PyTorch, no TensorFlow, no JAX.

### B.5 — GPU availability

```
$ ls /dev/dri/        → No such file or directory
$ ls /dev/nvidia*     → No such file or directory
$ nvidia-smi          → command not found
$ nvcc --version      → not installed
```

**Result: No GPU, no CUDA, no cuDNN. Hardware-incapable of running any neural video inference even if a model existed.**

### B.6 — What the providers actually do

`app/providers/`:

| File | Lines | What it actually does | Has neural weights? |
|------|-------|----------------------|---------------------|
| `local_provider.py` | 316 | Real local generation via **FFmpeg lavfi filters** (testsrc2, color, drawtext, hue). Procedural, NOT neural. | NO |
| `test_provider.py` | 145 | Deterministic stub for tests | NO |
| `neural_interface.py` | 228 | Interface ONLY — defines `NeuralCapability`, `ProviderClassification`, `NeuralRuntimeState`, `GenerationMode`, `detect_hardware()`, `enforce_local_only()`. Explicitly states: "This module does NOT include any neural model." | NO |
| `runway.py` | 186 | CLOUD stub — would call Runway API. **Blocked by LOCAL_ONLY**, no API key. | NO |
| `pika.py` | 162 | CLOUD stub — would call Pika API. **Blocked by LOCAL_ONLY**, no API key. | NO |
| `base.py` | 246 | Abstract `VideoProviderAdapter` interface | NO |
| `registry.py` | 15 | Provider registry | NO |
| `__init__.py` | 25 | Provider imports | NO |

`local_provider.py` line 4 (module docstring):
> "Performs REAL local video generation using FFmpeg. No cloud APIs. No mock providers. No placeholder artifacts."

`local_provider.py` line 88:
```python
def _check_ffmpeg(self) -> None:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, ...)
```

`local_provider.py` line 268:
```python
return LegacyGenerationResponse(
    provider_job_id=...,
    status=GenerationStage.COMPLETED.value,
    video_url=output_path,  # local filesystem path
    ...
    metadata={"runtime": "ffmpeg", ...}
)
```

The `local_cinematic_v1` is the **identifier** of the FFmpeg-based local provider, not a real model.

### B.7 — What the "model" files in source actually do

`app/services/vision_runtime.py`, `vision_segmentation.py`, `vision_depth.py`, `visual_analyzer.py`, `segmentation_service.py`, `capability_registry.py`, `providers/neural_interface.py` — these contain **capability-detection code** that *would* call `torch.cuda.is_available()` if torch were installed, but they all gracefully degrade to CPU/no-op when torch is absent. They never import any actual model class. They never load any weights. They never run any inference. They are stubs/adapters for a future neural capability.

**Verdict: NO neural video model exists, NO neural video model has ever existed in this repository, NO neural video model can exist on this hardware.**

---

## PART C — DOES MAKE QUALIFY AS "PROPRIETARY NEURAL VIDEO MODEL"?

| Required (per audit) | Status | Evidence |
|----------------------|--------|----------|
| 1. Actual learned model weights | **MISSING** | 0 weight files in repo; 0 ML libraries installed; 0 ML libraries in requirements.txt |
| 2. Actual neural architecture | **MISSING** | 0 `nn.Module` subclasses; 0 diffusion / DiT / UNet / VAE / transformer / attention references in source; 0 "make" video model code |
| 3. Actual executable inference path | **MISSING** | No `model(input)` call, no `pipeline()` call, no `generate()` call on a neural network; only `subprocess.run(["ffmpeg", ...])` |
| 4. Actual video generation capability (neural) | **MISSING** | Video IS generated, but via FFmpeg lavfi procedural filters, NOT neural inference |
| 5. Clear ownership/identity as MAKE's model | **N/A** | Nothing to own |

**Conclusion: MAKE does NOT contain a proprietary neural video model. MAKE contains a sophisticated orchestration, vision, transformation, and procedural-generation system — but no neural network weights, no neural architecture, no neural inference.**

The video MAKE produces today is the output of `ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=24:duration=3 -vf "hue=h=...:s=...,drawtext=..."` — procedural cinematic placeholder. It is a real, valid MP4, but it is **NOT a learned model output**. The orchestrator, director, color engine, transformation engine, vision engine, etc. are all real, all functional, all testable — but they operate on a procedural substrate, not a neural substrate.

---

## PART D — MAKE MODEL IDENTITY (NAMESPACE SEARCH)

Searched for: `MAKE Neural`, `MAKE Video Model`, `MAKE Foundation`, `MAKE-V1`, `MAKE-V2`, `MAKE Diffusion`, `MAKE Transformer`, `MAKE Cinema`, `MAKE Motion`, `MAKE Generative Video`, `MAKE Neural Engine`, `MAKE Video Intelligence`, `MAKE Foundation Model`.

| Term | Found? | What it actually refers to |
|------|--------|----------------------------|
| `MAKE Neural` | none in source | — |
| `MAKE Foundation` | none in source | — |
| `MAKE-V1` / `MAKE-V2` | none in source | — |
| `MAKE Diffusion` | none in source | — |
| `MAKE Transformer` | none in source | — |
| `MAKE Cinema` | docs only (`MAKE_CINEMA_ENGINE.md`) | Software service: camera-move / shot-composition planner. NOT a model. |
| `MAKE Motion` | docs only (`MAKE_MOTION_ENGINE.md`) | Motion planning service. NOT a model. |
| `MAKE Generative Video` | docs only | Aspirational documentation. NOT a model. |
| `MAKE Neural Engine` | none in source | — |
| `MAKE Video Intelligence` | none in source | — |
| `MAKE ONE` | docs (`MAKE_ONE.md`) | Routing / clarification / smart-prompt service. NOT a model. |
| `MAKE Auto` | docs (`MAKE_AUTO.md`) | Routing service. NOT a model. |
| `Director` | source | Software: planning, intent, shot list. NOT a model. |
| `Creative Director` | docs | Same as Director. NOT a model. |
| `Genesis` | docs (`MAKE_GENESIS.md`) | Concept-exploration service. NOT a model. |
| `Universal Model Engine` | source | Provider aggregator. NOT a model. |
| `Model Router` / `Router4` | source | Provider-selection logic. NOT a model. |
| `Model Lab` | source | Model registry/UI. NOT a model. |
| `Vision Engine` | source | Vision analysis pipeline. NOT a model. |

**Verdict: None of the MAKE-Named concepts correspond to a real trained neural model. They are all software services around generation, not the generator itself.**

---

## PART E — TRAINING INFRASTRUCTURE

| Item | Found? |
|------|--------|
| Training scripts (`train*.py`, `training*.py`, `finetune*.py`, `pretrain*.py`) | 0 |
| Dataset loaders (`dataset*.py`, `dataloader*.py`) | 0 |
| Video datasets (WebVid, UCF-101, Kinetics, etc.) | 0 |
| Frame processing / captioning code | 0 |
| Optimizer / loss / scheduler code (`torch.optim.*`, `AdamW`, `def training_step`, etc.) | 0 |
| Hyperparameter / config for training | 0 |
| Distributed training launcher (`torchrun`, `accelerate launch`) | 0 |
| GPU training rig / cluster config | 0 (no GPU at all) |
| Training data storage | 0 |
| Model registry with learned weights | 0 |

**Verdict: Zero training infrastructure. There is no path in this repo by which a neural model could be trained, even if a GPU and 10 TB of data were suddenly available.**

---

## PART F — PUBLIC GENERATION E2E VERIFICATION (THROUGH CLOUDFLARE TUNNEL)

### F.1 — End-to-end flow (verified externally, not from localhost)

Performed a real public E2E through `https://anytime-telecharger-advantages-antivirus.trycloudflare.com/`:

```
Step  Method  Path                                Status
1     GET     /                                   200 (909 bytes vite HTML)
2     GET     /api/v1/                            200 (65 bytes  MAKE root info)
3     POST    /api/v1/auth/register               201 (created audit3@makevideo.io)
4     POST    /api/v1/auth/token                  200 (JWT issued)
5     POST    /api/v1/projects                    201 (project be05f9d4-...)
6     POST    /api/v1/generation                  201 (job ae929422-...)
7     GET     /api/v1/generation/{id}/status      200 (status=completed in 6s)
8     GET     /api/v1/files/projects/.../...mp4    200 (24,916 bytes, video/mp4)
```

The job's `result.media_info` from the orchestrator:
```
{
  "duration_seconds": 3.0,
  "width": 1280,
  "height": 720,
  "fps": 24.0,
  "codec_name": "h264",
  "pixel_format": "yuv420p",
  "bit_rate": 63408,
  "file_size_bytes": 24916,
  "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
}
```

### F.2 — ffprobe confirmation (the file we got back is a real MP4)

```
$ ffprobe /tmp/tunnel_video.mp4
[STREAM]
codec_name=h264
width=1280
height=720
pix_fmt=yuv420p
r_frame_rate=24/1
duration=3.000000
bit_rate=63408
nb_frames=72
TAG:encoder=Lavc61.19.101 libx264
[FORMAT]
format_name=mov,mp4,m4a,3gp,3g2,mj2
duration=3.000000
size=24916
TAG:encoder=Lavf61.7.100
```

**The file received via the public tunnel is a real, valid, playable H.264 MP4 file.**

### F.3 — What the file actually IS

It is the output of FFmpeg's `lavfi` (libavfilter) source generators:
- `testsrc2` for the base video (FFmpeg's built-in test pattern)
- `hue` filter for mood-based color (hue + saturation derived from MD5 of the prompt)
- `drawtext` for an on-screen caption with the prompt and seed
- `aevalsrc` / `sine` for procedural audio
- Duration / resolution / fps are all real, generated via FFmpeg

**The file is real, but it is NOT the output of a learned neural model.** It is the output of FFmpeg procedural filters. The prompt is hashed with MD5 to deterministically pick a hue/saturation and a caption; the underlying video frames come from a test pattern, not from a generator network.

### F.4 — Fixes applied during this audit

1. `app/services/orchestrator.py` lines 199-216: the orchestrator was calling `httpx.get(result.video_url)` even when `video_url` was a local filesystem path, causing `Download failed: Request URL is missing an 'http://' or 'https://' protocol.` Fixed to detect `file://`, `/...`, `./...`, and Windows `C:\...` paths and use `shutil.copyfile` instead. (This was a bug that prevented the orchestrator from completing the local-provider flow; the underlying FFmpeg generation worked, the orchestrator just couldn't pick up the result.)
2. No other code changes.
3. No new providers, no new engines, no new architecture.
4. No cloud API calls anywhere.
5. No third-party models installed.

---

## PART G — PROPRIETARY MODEL GAP ANALYSIS

### G.1 — The honest statement

MAKE today is a **production-grade orchestration and procedural-generation system**. It has:

- 156 services, 28 routers, 22 test files, 393 passing tests
- Real local video generation (FFmpeg lavfi, real MP4s)
- A vision engine, transformation engine, director, model router, model lab
- A universal model engine that aggregates providers
- A neural interface (interface only — no model)
- Full provenance, audit trail, and orchestration

MAKE does NOT have:

- A single neural network weight file
- A single line of diffusion / DiT / UNet / transformer / VAE code
- A single ML library installed (no torch, no diffusers, no transformers, no onnx, no accelerate)
- A single training script
- A GPU to run neural inference
- A dataset to train on
- Any path from the current state to a real learned video model

### G.2 — What "MAKE PROPRIETARY NEURAL VIDEO MODEL" would require

To make the statement `MAKE has a proprietary neural video model` actually true, the following would all need to exist (none of which currently do):

| # | Requirement | Current state |
|---|-------------|---------------|
| 1 | At least one trained checkpoint file (`*.safetensors`, `*.pt`, `*.onnx`, `*.engine`) | 0 files in repo |
| 2 | A model architecture definition (DiT, 3D UNet, video transformer, etc.) | 0 `nn.Module` classes |
| 3 | An inference path that loads the checkpoint and calls `model(input)` | Only `subprocess.run(["ffmpeg", ...])` |
| 4 | A training pipeline (dataset + dataloader + loss + optimizer + training loop) | 0 training code |
| 5 | Training data (video-text pairs, e.g. WebVid, internal) | 0 datasets |
| 6 | Compute (GPU, multi-day training run) | 0 GPU; 15 GB disk free |
| 7 | Inference compute (GPU or fast CPU, plus the model itself) | 0 GPU; no model |
| 8 | A clear naming/identity scheme (MAKE-V1, MAKE-Foundation, etc.) | Names exist only in docs, not in code |
| 9 | An evaluation protocol (FVD, IS, human eval) | 0 evaluation code |
| 10 | A way to verify the model is actually MAKE's, not a third-party wrapper | Nothing to verify |

### G.3 — Honest competitive framing

- **Procedural / non-neural**: MAKE generates real, valid, viewable MP4 files locally. The orchestrator, vision engine, transformation engine, director, and editing systems are real. This is genuinely useful as a deterministic, no-cloud, no-API-key local runtime.
- **Neural**: MAKE has no neural video model. It does not compete with Runway / Pika / Sora / Kling / Veo / Wan / Hunyuan / LTX-Video on the actual neural-quality axis. Any claim that "MAKE has a proprietary neural video model" would be FALSE.
- **Architectural**: MAKE's design (provider abstraction, capability detection, hardware-aware degradation, model router, model lab, local-first) is genuinely well-suited to *integrating* a neural model in the future. The interface (`NeuralCapability`, `ProviderClassification`, `GenerationMode`, `enforce_local_only`) is in place. There is no model behind it.

### G.4 — What would close the gap

In order of increasing cost and time:

1. **Pin and install a small, real, neural video model** (e.g. `diffusers` with `AnimateDiff-Lightning` 4-step distilled, ~4 GB) and a CPU-friendly runtimes path (OpenVINO, ONNX Runtime, or a small SVD distilled). This is the only honest way to claim a "local neural" model.
2. **Train any model from scratch** (requires GPU, dataset, weeks of compute, evaluation, safety review). The repository has none of this infrastructure and no path to it.
3. **Acquire / license a third-party model and properly attribute it** (e.g. LTX-Video, Wan2.1, HunyuanVideo, Mochi) with clear license and provenance. This would still NOT be "MAKE's own" model; it would be a third-party model integrated into MAKE.

### G.5 — What is NOT in scope (per audit rules)

- No third-party model is to be installed
- No cloud API call is to be made
- No existing architecture is to be modified
- No `LocalProvider` is to be replaced
- No third-party model is to be introduced to make a test pass

All of these constraints are honored. The fixes in this audit were limited to: (a) `app/services/orchestrator.py` to handle local file paths in the same way the existing `file://` handler did; (b) `backend/.env` CORS for the new tunnel; (c) no other code changes.

---

## PART H — VERIFICATION SUMMARY

```
STATUS:
  Part A  (Public status)        VERIFIED
  Part B  (Forensic weights)     0/0 files, 0 ML libs, 0 GPU
  Part C  (Proprietary model?)   NO — zero neural network evidence
  Part D  (MAKE model identity)  NO — all names refer to software services
  Part E  (Training infra)       0 scripts, 0 datasets, 0 GPU
  Part F  (Public E2E)           VERIFIED through public tunnel
  Part G  (Gap analysis)         DOCUMENTED

PUBLIC URL:        https://anytime-telecharger-advantages-antivirus.trycloudflare.com/
ORIGIN:            vite 0.0.0.0:5173 → /api/* → 127.0.0.1:8000 (FastAPI)
PORT 8000 EXPOSED: NO (only via vite proxy)
DB/REDIS/SHELL:    NOT exposed
LOCAL_ONLY:        ENABLED
CLOUD PROVIDERS:   DISABLED (no keys, blocked by enforce_local_only)

GENERATION TEST (through public tunnel, this audit):
  POST /api/v1/generation  → 201 (job=ae929422-...)
  GET /api/v1/generation/{id}/status → 200 status=completed in 6s
  GET /api/v1/files/projects/.../...mp4 → 200, video/mp4, 24,916 bytes
  ffprobe confirms: H.264, 1280x720, yuv420p, 24 fps, 3.0s, 72 frames

OUTPUT TYPE:       Real MP4 (FFmpeg lavfi procedural — NOT neural)
FFMPEG:            7.1.1 (freshly installed)
ML LIBRARIES:      NONE
GPU:               NONE
```

---

## PART I — UNQUALIFIED CONCLUSIONS

1. **MAKE does NOT contain a proprietary neural video model.** There is no model — no weights, no architecture, no inference path, no training code, no GPU, no dataset. The repository is in a state that is "ready to receive a model" but does not contain one.

2. **MAKE's public tunnel is real and works end-to-end.** A real, valid, playable MP4 was generated and retrieved through the public HTTPS URL in this audit.

3. **The generated video is procedural (FFmpeg lavfi), not neural.** The MP4 is real, but its content comes from FFmpeg's `testsrc2` test pattern, color filters, and `drawtext`. It is not the output of a learned video diffusion / video transformer model. The orchestrator, router, vision, and transformation layers are all real, but they operate on a procedural substrate.

4. **No claim of "MAKE's own neural model" is supportable from this repository's current state.** Any such claim would be invented functionality.

5. **The neural interface is in place but empty.** `app/providers/neural_interface.py` defines the API surface (`NeuralCapability`, `ProviderClassification`, `NeuralRuntimeState`, `GenerationMode`, `detect_hardware()`, `enforce_local_only()`) for a future neural runtime. The runtime itself does not exist.

6. **No third-party model was installed, no cloud API was called, no existing architecture was modified beyond one orchestrator bugfix and a CORS config update.**

7. **All services remain running** after this audit:
   - cloudflared → bgp_06723cbe60016lWnEpi36M7NfC (tunnel to vite 5173)
   - vite → bgp_06723ca9a0012arbbSEmQ2cAGV (0.0.0.0:5173)
   - uvicorn → bgp_0672a54f1001GQ26fXw6RU2mXo (0.0.0.0:8000)

---

END OF AUDIT
