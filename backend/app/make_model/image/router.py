"""
FastAPI router for the MAKE image subsystem.

Exposes endpoints that an iOS client can hit (with auth) to:

  POST /api/v1/image/generate        - generate a single image
  POST /api/v1/image/train           - trigger a CPU training run (synchronous)
  GET  /api/v1/image/status          - model status, checkpoint info, recent samples
  GET  /api/v1/image/samples         - list recent generated samples
  GET  /api/v1/image/exports/{id}    - download a generated image (PNG)

The router is mobile-friendly: small JSON payloads, no streaming, large
operations are bounded by server-side step limits.
"""

from __future__ import annotations

import os
import time
import glob
import json
import base64
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.make_model.utils import get_logger, now_iso, sha256_file
from app.make_model.image.inference.sampler import ImageSampler, SamplerConfig
from app.make_model.image.training.trainer import ImageTrainer, TrainingConfig
from app.make_model.image.dataset.acquire import acquire_image_dataset, load_image_arrays
from app.make_model.image.registry_bridge import ImageRegistryBridge
from app.make_model.image.arch.unet import count_params
from app.make_model.registry import get_registry
from app.make_model.state import ModelState

logger = get_logger("make_model.image.router")


router = APIRouter(prefix="/api/v1/image", tags=["image"])


# --- schemas ----------------------------------------------------------------


class GenerateRequest(BaseModel):
    prompt: str = ""
    seed: int = 0
    num_inference_steps: int = 30
    image_size: int = 32
    checkpoint_path: Optional[str] = None
    output_format: str = "png"
    # Image-to-image parameters
    init_image_path: Optional[str] = None
    init_strength: float = 0.6
    # Batch parameters
    batch_size: int = 1


class GenerateResponse(BaseModel):
    ok: bool
    outputs: List[Dict[str, Any]] = Field(default_factory=list)


class TrainRequest(BaseModel):
    steps: int = Field(default=30, ge=1, le=2000)
    image_size: int = Field(default=32, ge=8, le=64)
    base_channels: int = Field(default=16, ge=4, le=64)
    num_res_blocks: int = Field(default=2, ge=1, le=4)
    num_timesteps: int = Field(default=80, ge=10, le=200)
    batch_size: int = Field(default=4, ge=1, le=8)
    learning_rate: float = 3e-4
    save_every: int = Field(default=20, ge=1)
    procedural_count: int = Field(default=128, ge=8, le=2048)
    seed: int = 0
    sample_after: bool = True
    sample_prompt: str = "a structured colored gradient"
    sample_steps: int = 25


class TrainResponse(BaseModel):
    ok: bool
    steps_done: int
    final_loss: float
    elapsed_seconds: float
    checkpoint_path: str
    checkpoint_sha256: str
    parameters: int
    dataset_kind: str
    dataset_name: str
    sample_path: Optional[str] = None
    created_at: str


class StatusResponse(BaseModel):
    ok: bool
    overall_state: str
    model_count: int
    checkpoint_count: int
    training_run_count: int
    latest_checkpoint_sha256: Optional[str]
    latest_checkpoint_step: Optional[int]
    latest_sample_path: Optional[str]
    latest_sample_sha256: Optional[str]
    hardware: dict
    note: str


# --- helpers ----------------------------------------------------------------


def _latest_sample_dir() -> str:
    p = os.environ.get("MAKE_MODEL_ROOT", "/tmp/make_model_artifacts")
    return os.path.join(p, "exports", "images")


def _latest_checkpoint() -> Optional[str]:
    reg = get_registry()
    cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
    if not cps:
        return None
    return sorted(cps, key=lambda c: c.get("created_at", ""))[-1]


def _verify_checkpoint_path(path: str) -> str:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"checkpoint not found: {path}")
    return path


# --- endpoints --------------------------------------------------------------


@router.post("/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest):
    cp = req.checkpoint_path or (_latest_checkpoint() or {}).get("path")
    if not cp or not os.path.exists(cp):
        raise HTTPException(status_code=409, detail="No trained checkpoint available. Train first via /image/train.")
    _verify_checkpoint_path(cp)
    sampler = ImageSampler()
    cfg = SamplerConfig(
        model_name=ImageRegistryBridge.IMAGE_MODEL_NAME,
        checkpoint_path=cp,
        prompt=req.prompt,
        seed=req.seed,
        num_inference_steps=req.num_inference_steps,
        image_size=req.image_size,
        output_format=req.output_format,
        init_image_path=req.init_image_path or "",
        init_strength=req.init_strength,
    )
    out = []
    n = max(1, min(int(req.batch_size), 8))
    for i in range(n):
        cfg_i = SamplerConfig(**{**cfg.to_dict(), "seed": req.seed + i})
        res = sampler.sample(cfg_i)
        if not res.ok:
            raise HTTPException(status_code=500, detail=res.message)
        ImageRegistryBridge().mark_inference_ready(res.output_path, res.output_sha256)
        out.append({
            "output_path": res.output_path,
            "output_url": f"/api/v1/image/exports/{os.path.basename(res.output_path)}",
            "width": res.width,
            "height": res.height,
            "sha256": res.output_sha256,
            "bytes": res.output_bytes,
            "elapsed_seconds": res.elapsed_seconds,
            "inference_steps": res.inference_steps,
            "model_name": res.model_name,
            "checkpoint_sha256": res.checkpoint_sha256,
            "generation_resolution_native": res.generation_resolution_native,
            "refinement_resolution_native": res.refinement_resolution_native,
            "interpolation_note": res.interpolation_note,
            "kind": res.kind,
            "created_at": res.created_at,
        })
    return GenerateResponse(ok=True, outputs=out)


@router.post("/train", response_model=TrainResponse)
async def train(req: TrainRequest):
    root = os.environ.get("MAKE_MODEL_ROOT") or None
    bridge = ImageRegistryBridge()
    info = acquire_image_dataset(
        out_root=root, target_size=req.image_size,
        procedural_count=req.procedural_count, seed=req.seed,
    )
    arr = load_image_arrays(info, target_size=req.image_size)
    from app.make_model.image.arch.unet import NumpyUNet, NumpyUNetConfig
    ucfg = NumpyUNetConfig(
        image_size=req.image_size,
        base_channels=req.base_channels,
        num_res_blocks=req.num_res_blocks,
        num_timesteps=req.num_timesteps,
    )
    _m = NumpyUNet(ucfg, seed=req.seed)
    n_params = count_params(_m)
    bridge.register_model(n_params, ucfg.to_dict())

    run_id = f"img-{int(time.time())}"
    cfg = TrainingConfig(
        image_size=req.image_size,
        base_channels=req.base_channels,
        num_res_blocks=req.num_res_blocks,
        num_timesteps=req.num_timesteps,
        batch_size=req.batch_size,
        max_steps=req.steps,
        save_every=req.save_every,
        learning_rate=req.learning_rate,
        seed=req.seed,
        dataset_kind=info.kind,
        dataset_name=info.name,
        dataset_manifest_sha=info.sha256_manifest,
        notes=f"triggered via /image/train",
    )
    bridge.register_training_run(run_id, cfg.to_dict(), info.to_dict(), req.steps)
    trainer = ImageTrainer(cfg, out_root=root)
    result = trainer.train(arr, info.to_dict())
    bridge.register_checkpoint(
        checkpoint_path=result.checkpoint_path,
        training_run_id=run_id,
        config=cfg.to_dict(),
        dataset_info=info.to_dict(),
        global_step=result.steps_done,
        metric_summary={"final_loss": result.final_loss, "loss_curve": result.loss_curve},
        notes=f"via router, elapsed={result.elapsed_seconds}",
    )
    bridge.finalize_training_run(run_id, result.steps_done, result.final_loss, result.checkpoint_path)

    sample_path = None
    if req.sample_after:
        sampler = ImageSampler(out_root=root)
        scfg = SamplerConfig(
            model_name=bridge.IMAGE_MODEL_NAME,
            checkpoint_path=result.checkpoint_path,
            prompt=req.sample_prompt,
            seed=42,
            num_inference_steps=req.sample_steps,
            image_size=req.image_size,
        )
        sres = sampler.sample(scfg)
        sample_path = sres.output_path
        bridge.mark_inference_ready(sres.output_path, sres.output_sha256)

    return TrainResponse(
        ok=True,
        steps_done=result.steps_done,
        final_loss=result.final_loss,
        elapsed_seconds=result.elapsed_seconds,
        checkpoint_path=result.checkpoint_path,
        checkpoint_sha256=result.checkpoint_sha256,
        parameters=result.parameters,
        dataset_kind=info.kind,
        dataset_name=info.name,
        sample_path=sample_path,
        created_at=now_iso(),
    )


@router.get("/status", response_model=StatusResponse)
async def status():
    reg = get_registry()
    s = reg.get_status()
    cps = [c for c in s["checkpoints"] if c["model_name"] == ImageRegistryBridge.IMAGE_MODEL_NAME]
    latest = sorted(cps, key=lambda c: c.get("created_at", ""))[-1] if cps else None
    sample_dir = _latest_sample_dir()
    samples = []
    if os.path.isdir(sample_dir):
        for fn in sorted(os.listdir(sample_dir)):
            if fn.endswith(".png"):
                samples.append(os.path.join(sample_dir, fn))
    latest_sample = samples[-1] if samples else None
    return StatusResponse(
        ok=True,
        overall_state=s["overall_state"],
        model_count=s["model_count"],
        checkpoint_count=s["checkpoint_count"],
        training_run_count=s["training_run_count"],
        latest_checkpoint_sha256=latest["sha256"] if latest else None,
        latest_checkpoint_step=latest["global_step"] if latest else None,
        latest_sample_path=latest_sample,
        latest_sample_sha256=sha256_file(latest_sample) if latest_sample else None,
        hardware={
            "device": "cpu",
            "cuda_available": False,
            "pytorch_available": False,
            "cpu_count": os.cpu_count(),
        },
        note="Native CPU image generation. No GPU. No external AI API. "
             "Resolution is 32x32 native unless retrained at larger size.",
    )


@router.get("/samples")
async def list_samples(limit: int = Query(20, ge=1, le=200)):
    sample_dir = _latest_sample_dir()
    if not os.path.isdir(sample_dir):
        return {"samples": []}
    out = []
    for fn in sorted(os.listdir(sample_dir), reverse=True):
        if not fn.endswith(".png"):
            continue
        full = os.path.join(sample_dir, fn)
        prov = full + ".provenance.json"
        meta = {}
        if os.path.exists(prov):
            try:
                meta = json.load(open(prov))
            except Exception:
                pass
        out.append({
            "filename": fn,
            "url": f"/api/v1/image/exports/{fn}",
            "bytes": os.path.getsize(full),
            "sha256": sha256_file(full),
            "created_at": meta.get("created_at", ""),
            "seed": meta.get("seed"),
            "prompt": meta.get("prompt", ""),
            "inference_steps": meta.get("inference_steps"),
            "generation_resolution_native": meta.get("generation_resolution_native"),
        })
        if len(out) >= limit:
            break
    return {"samples": out}


@router.get("/exports/{filename}")
async def export_file(filename: str):
    # path-traversal protection
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    sample_dir = _latest_sample_dir()
    full = os.path.join(sample_dir, filename)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(full, media_type="image/png")


@router.get("/ping")
async def ping():
    return {"ok": True, "subsystem": "make_image", "ts": now_iso()}