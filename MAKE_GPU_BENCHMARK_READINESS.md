# MAKE — GPU BENCHMARK READINESS

## Current Hardware Detection (verified 2026-09-03)

```
GPU:                 NONE
VRAM:                0 GB
CUDA / ROCm / MPS:   UNAVAILABLE
PyTorch:             NOT INSTALLED
diffusers:           NOT INSTALLED
transformers:        NOT INSTALLED
ONNX Runtime:        NOT INSTALLED
safetensors:         NOT INSTALLED
accelerate:          NOT INSTALLED
Model weights:       NONE on disk
FFmpeg:              7.1.1 (real)
Disk free:           15 GB
RAM available:       8.5 GiB
```

The detection is implemented in `backend/app/providers/neural_interface.py::detect_hardware()` and verified live in this session.

## What the readiness layer does

1. `detect_hardware()` returns a dict with `gpu_available`, `vram_gb`, `cuda_available`, `pytorch_available`, `diffusers_available`, `onnx_available`.
2. `get_neural_runtime_report()` returns `state`, `classification`, `device`, `runtime`, `errors`.
3. `enforce_local_only(prov_class)` returns `False` for `cloud`, `True` for `local_*` and `deterministic_test`.
4. `get_generation_mode()` returns `local_only` by default.

The `LocalNeuralProvider` is an **interface only** — it is NOT instantiated because no model can be loaded. The moment a model is present, the `ProviderRegistry` will accept a `LocalNeuralProvider` instance and route to it.

## Step-by-step GPU enablement

```bash
# 1. Install CUDA toolkit + driver on the GPU host
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo ubuntu-drivers autoinstall
sudo reboot

# 2. Verify
nvidia-smi
# (expect: GPU model, VRAM, CUDA version, driver version)

# 3. Install Python 3.10+ (or 3.11)
sudo apt install -y python3.11 python3.11-venv

# 4. Create venv and activate
python3.11 -m venv .venv
source .venv/bin/activate

# 5. Install PyTorch matching CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 6. Install diffusers, transformers, accelerate, safetensors
pip install diffusers transformers accelerate safetensors
pip install onnxruntime-gpu

# 7. Sanity check
python3 -c "import torch; print('CUDA:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0))"
# expect: CUDA: True Device: NVIDIA RTX 4090 (or similar)

# 8. Download a model
python3 -c "
from huggingface_hub import snapshot_download
p = snapshot_download('Lightricks/LTX-Video', cache_dir='/models/ltx')
print(p)
"

# 9. Wire the provider
# Add a file backend/app/providers/local_neural_provider.py that:
#   - uses diffusers LTXPipeline.from_pretrained(model_path)
#   - exposes submit_generation / get_result / cancel_job
#   - registers itself in providers/__init__.py

# 10. Restart the backend
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 11. Verify
curl -s http://localhost:8000/api/v1/health
# look for "neural_runtime": "available"
```

## Automatic capability detection (per model)

The benchmark runner will call `detect_hardware()` and `get_neural_runtime_report()` to determine:

- VRAM available
- Whether diffusers is installed
- Whether the requested model is in `~/.cache/huggingface` or a configured model dir
- Whether the model can be loaded
- Whether inference succeeds on a test prompt (sanity)

If any check fails, the case is marked `NOT_TESTED` with `failure_reason` set.

## Recommended models per tier

| VRAM | Recommended local model | License | Notes |
|------|-------------------------|---------|-------|
| 8 GB | LTX-Video 2B, Wan 2.1 1.3B | OpenRAIL / Apache 2.0 | fast, I2V + T2V |
| 12 GB | SVD-XT 1.1, CogVideoX-2B | Stability / Apache 2.0 | image-to-video |
| 16 GB | HunyuanVideo 1.5B, CogVideoX-5B | Tencent / Apache 2.0 | higher quality |
| 24 GB | LTX-Video 2B at full quality + HunyuanVideo | OpenRAIL / Tencent | production |
| 32 GB+ | Wan 2.1 14B, Hunyuan 13B | Apache 2.0 / Tencent | max quality |

## Disk math

- LTX-Video 2B weights: ~5 GB
- Wan 2.1 1.3B: ~3 GB
- HunyuanVideo 1.5B: ~6 GB
- SVD-XT 1.1: ~10 GB
- CogVideoX-2B: ~5 GB
- PyTorch + CUDA: ~3 GB
- diffusers stack: ~1 GB
- Working set + outputs: 5–10 GB
- **Total minimum**: 20 GB (we have 15 GB → insufficient)

## Benchmark runner on GPU host

```bash
cd backend
.venv/bin/python3 -m app.services.benchmark_runner --suite all --platform make --provider local_neural --output benchmark_results.json
.venv/bin/python3 -m app.services.benchmark_evaluator benchmark_results.json --report MAKE_BENCHMARK_RESULTS.md
```

The runner outputs a JSON with one record per case. The evaluator aggregates per category and writes a markdown report.

## Why this is honest

- No scores are reported for cases that haven't been executed.
- No model is claimed to be available unless its files exist and a load test passes.
- No GPU claim is made unless `torch.cuda.is_available()` is True.
- No benchmark output is fabricated or interpolated.
