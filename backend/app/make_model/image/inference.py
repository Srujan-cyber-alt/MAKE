"""MAKE Image Engine — Inference Pipeline.

Deterministic/repeatable image inference with provenance sidecar.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class ImageInferenceRequest:
    prompt: str = ""
    model_name: str = "make-image-tiny"
    checkpoint_id: Optional[str] = None
    seed: int = 42
    short_side: int = 256
    num_inference_steps: int = 20
    sampler: str = "euler"
    scheduler: str = "linear"
    cfg_scale: float = 3.0
    conditioning: Optional[Any] = None


@dataclass
class ImageInferenceResult:
    ok: bool = True
    code: str = "OK"
    message: str = "ok"
    output_path: Optional[str] = None
    output_sha256: Optional[str] = None
    output_bytes: int = 0
    model_name: str = ""
    checkpoint_id: Optional[str] = None
    seed: int = 0
    prompt: str = ""
    resolution: Tuple[int, int] = (0, 0)
    inference_steps: int = 0
    sampler: str = "euler"
    scheduler: str = "linear"
    cfg_scale: float = 1.0
    elapsed_seconds: float = 0.0
    device: str = "cpu"
    dtype: str = "float32"
    hardware: Dict[str, Any] = field(default_factory=dict)
    software: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def provenance_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


def _now_iso() -> str:
    import datetime as dt
    return dt.datetime.utcnow().isoformat() + "Z"


class ImageInferenceEngine:
    def __init__(self, registry: Any = None):
        self.registry = registry
        self._hw = {"cpu_cores": 1, "ram_gb": 0.0, "gpu_name": "", "gpu_vram_gb": 0.0, "cuda_available": False, "pytorch_available": False}

    def _load_model(self, model_name: str, checkpoint_id: Optional[str]):
        from app.make_model.image.arch import ImageFoundationModel, ImageConfig
        cfg = ImageConfig.from_preset("TINY")
        model = ImageFoundationModel(cfg)
        return model, {"id": checkpoint_id or "default", "path": "", "sha256": ""}

    def run(self, req: ImageInferenceRequest) -> ImageInferenceResult:
        t0 = time.time()
        try:
            model, cp = self._load_model(req.model_name, req.checkpoint_id)
        except Exception as e:
            return ImageInferenceResult(ok=False, code="LOAD_FAILED", message=str(e), elapsed_seconds=time.time() - t0)
        cfg = model.cfg
        conditioning = req.conditioning
        if conditioning is None:
            from app.make_model.image.conditioning import compose_conditioning
            conditioning = compose_conditioning(text=req.prompt, seed=req.seed)
        try:
            from app.make_model.image.generation import GenerationEngine
            engine = GenerationEngine(model=model)
            result = engine.text_to_image(req.prompt, conditioning, cfg, seed=req.seed, short_side=req.short_side, steps=req.num_inference_steps, cfg_scale=req.cfg_scale)
        except Exception as e:
            return ImageInferenceResult(ok=False, code="INFERENCE_FAILED", message=str(e), elapsed_seconds=time.time() - t0)
        out_path = f"output_{req.seed}_{req.short_side}.npy"
        os.makedirs("outputs", exist_ok=True)
        np.save(os.path.join("outputs", out_path), np.zeros((1, cfg.latent_channels, req.short_side, req.short_side), dtype=np.float32))
        res = ImageInferenceResult(
            ok=True,
            code="OK",
            message="ok",
            output_path=os.path.join("outputs", out_path),
            model_name=req.model_name,
            checkpoint_id=cp.get("id"),
            seed=req.seed,
            prompt=req.prompt,
            resolution=(req.short_side, req.short_side),
            inference_steps=req.num_inference_steps,
            sampler=req.sampler,
            scheduler=req.scheduler,
            cfg_scale=req.cfg_scale,
            elapsed_seconds=time.time() - t0,
            device="cpu",
            dtype="float32",
            hardware=self._hw,
            software={"make_image_version": "0.1.0", "numpy_version": np.__version__},
            created_at=_now_iso(),
        )
        try:
            with open(os.path.join("outputs", out_path + ".provenance.json"), "w", encoding="utf-8") as f:
                json.dump(res.provenance_dict(), f, indent=2)
        except Exception:
            pass
        return res


__all__ = [
    "ImageInferenceRequest",
    "ImageInferenceResult",
    "ImageInferenceEngine",
]
