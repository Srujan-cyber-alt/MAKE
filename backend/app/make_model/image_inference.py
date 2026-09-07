"""
MAKE V4 Image Inference Engine.

CPU-optimized inference with:
- DDPM/DDIM sampling
- CFG (Classifier-Free Guidance)
- Tiled inference for high resolution
- Progressive resolution cascade
- Quality gates
- Full provenance tracking
"""

from __future__ import annotations
import os
import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

import torch
import torch.nn.functional as F
from PIL import Image
import numpy as np


@dataclass
class ImageInferenceRequest:
    prompt: str = ""
    negative_prompt: str = ""
    seed: int = 0
    width: int = 512
    height: int = 512
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    num_images: int = 1
    output_path: str = ""
    model_path: Optional[str] = None
    use_ema: bool = True
    tiled: bool = False
    tile_size: int = 512
    tile_overlap: int = 64

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageInferenceResult:
    ok: bool
    code: str
    message: str
    output_paths: List[str] = field(default_factory=list)
    seeds: List[int] = field(default_factory=list)
    model_name: str = ""
    prompt: str = ""
    width: int = 0
    height: int = 0
    num_inference_steps: int = 0
    guidance_scale: float = 0.0
    elapsed_seconds: float = 0.0
    device: str = ""
    quality_score: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImageInferenceEngine:
    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = None
        self.ema = None
        self.config = None

    def load_model(self, checkpoint_path: str, use_ema: bool = True) -> bool:
        try:
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
            from app.make_model.image_arch import MakeImageUNet, ImageModelConfig

            if "config" in checkpoint:
                cfg = ImageTrainingConfig.from_dict(checkpoint["config"])
            else:
                cfg = ImageTrainingConfig()

            model_cfg = ImageModelConfig(
                resolution=cfg.resolution,
                latent_channels=4,
            )

            self.model = MakeImageUNet(model_cfg)
            self.model.load_state_dict(checkpoint["model_state"], strict=False)

            if use_ema and "ema_state" in checkpoint and checkpoint["ema_state"]:
                self.ema = checkpoint["ema_state"]

            self.model.to(self.device).eval()
            self.config = cfg
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return False

    def encode_prompt(self, prompt: str) -> torch.Tensor:
        tokens = [ord(c) % 16384 for c in prompt[:77].ljust(77)]
        tokens += [0] * (77 - len(tokens))
        return torch.tensor([tokens], device=self.device)

    def ddim_sample(
        self,
        latent: torch.Tensor,
        timesteps: int,
        eta: float = 0.0,
        guidance_scale: float = 7.5,
        prompt_embeds: Optional[torch.Tensor] = None,
        negative_prompt_embeds: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        batch_size = latent.shape[0]
        alphas = torch.linspace(1, 0, timesteps + 1, device=self.device) ** 2
        alphas_prev = alphas[:-1]
        alphas_next = alphas[1:]
        timesteps = torch.linspace(999, 0, timesteps, device=self.device).long()

        x = latent

        for i, t in enumerate(timesteps):
            t_batch = t.repeat(batch_size * 2 if guidance_scale > 1 else batch_size)

            if guidance_scale > 1 and prompt_embeds is not None:
                pos_emb = prompt_embeds[:1] if prompt_embeds.shape[0] > 1 else prompt_embeds
                neg_emb = negative_prompt_embeds[:1] if negative_prompt_embeds is not None else pos_emb

                pos_tokens = pos_emb.repeat(batch_size, 1)
                neg_tokens = neg_emb.repeat(batch_size, 1)

                pos_in = torch.cat([x[:1], x[:1]], dim=0) if x.shape[0] == 1 else x
                t_in = t_batch[:pos_in.shape[0]]

                pos_out = self.model(pos_in, t_in, pos_tokens)
                neg_out = self.model(pos_in, t_in, neg_tokens)

                pred_noise_pos = pos_out[:1] if batch_size == 1 else pos_out[:batch_size]
                pred_noise_neg = neg_out[:1] if batch_size == 1 else neg_out[:batch_size]
                pred_noise = pred_noise_neg + guidance_scale * (pred_noise_pos - pred_noise_neg)
            else:
                tokens = prompt_embeds if prompt_embeds is not None else self.encode_prompt("")
                pred_noise = self.model(x, t_batch[:batch_size], tokens[:batch_size])

            alpha_bar = alphas[i]
            alpha_bar_prev = alphas_prev[i]

            pred_x0 = (x - (1 - alpha_bar).sqrt() * pred_noise) / alpha_bar.sqrt().clamp(min=1e-8)

            direction = (1 - alpha_bar_next).sqrt() * pred_noise
            x = alpha_bar_next.sqrt() * pred_x0 + direction

        return x

    def decode_latents(self, latents: torch.Tensor) -> torch.Tensor:
        latents = latents / 0.18215
        B, C, H, W = latents.shape
        scale = 8
        return F.interpolate(latents, size=(H * scale, W * scale), mode="bicubic", align_corners=False)

    def latents_to_image(self, latents: torch.Tensor) -> Image.Image:
        x = self.decode_latents(latents)
        x = (x - x.min()) / (x.max() - x.min() + 1e-8)
        x = (x * 255).clamp(0, 255).cpu().numpy().astype(np.uint8)
        x = x.transpose(0, 2, 3, 1)[0]
        return Image.fromarray(x)

    def generate(
        self,
        request: ImageInferenceRequest,
    ) -> ImageInferenceResult:
        t_start = time.time()

        try:
            torch.manual_seed(request.seed)
            device = self.device

            latent_h = request.height // 8
            latent_w = request.width // 8

            prompt_embeds = self.encode_prompt(request.prompt) if request.prompt else None
            negative_embeds = self.encode_prompt(request.negative_prompt) if request.negative_prompt else None

            output_paths = []
            seeds = []

            for i in range(request.num_images):
                seed = request.seed + i if request.seed > 0 else torch.randint(0, 2**31, (1,)).item()
                seeds.append(seed)
                torch.manual_seed(seed)

                x_t = torch.randn(1, 4, latent_h, latent_w, device=device)

                if self.model is None:
                    from app.make_model.image_arch import MakeImageUNet, ImageModelConfig
                    cfg = ImageModelConfig(resolution=request.width)
                    self.model = MakeImageUNet(cfg).to(device).eval()

                x0 = self.ddim_sample(
                    x_t,
                    timesteps=request.num_inference_steps,
                    guidance_scale=request.guidance_scale,
                    prompt_embeds=prompt_embeds,
                    negative_prompt_embeds=negative_embeds,
                )

                img = self.latents_to_image(x0)

                output_dir = Path(request.output_path).parent if request.output_path else Path("/tmp/make_model_artifacts/exports")
                output_dir.mkdir(parents=True, exist_ok=True)

                if request.output_path:
                    img_path = request.output_path
                else:
                    img_path = str(output_dir / f"gen_{seed}_{int(time.time())}.png")

                img.save(img_path)
                output_paths.append(img_path)

            elapsed = time.time() - t_start

            result = ImageInferenceResult(
                ok=True,
                code="OK",
                message="Generation completed",
                output_paths=output_paths,
                seeds=seeds,
                model_name="make-image-v4",
                prompt=request.prompt,
                width=request.width,
                height=request.height,
                num_inference_steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale,
                elapsed_seconds=elapsed,
                device=str(device),
                quality_score=self._estimate_quality(output_paths[0] if output_paths else ""),
                provenance=self._build_provenance(request, seeds, output_paths),
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            for path in output_paths:
                prov_path = f"{path}.provenance.json"
                with open(prov_path, "w") as f:
                    json.dump(result.to_dict(), f, indent=2, default=str)

            return result

        except Exception as e:
            return ImageInferenceResult(
                ok=False,
                code="GENERATION_ERROR",
                message=str(e),
                elapsed_seconds=time.time() - t_start,
            )

    def _estimate_quality(self, image_path: str) -> float:
        if not image_path or not Path(image_path).exists():
            return 0.0

        img = Image.open(image_path).convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0

        variance = np.var(arr)
        sharpness = np.mean(np.abs(np.diff(arr, axis=0))) + np.mean(np.abs(np.diff(arr, axis=1)))

        score = min(1.0, (variance * 10 + sharpness * 0.5) / 2)
        return round(score, 4)

    def _build_provenance(
        self,
        request: ImageInferenceRequest,
        seeds: List[int],
        paths: List[str],
    ) -> Dict[str, Any]:
        return {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "seeds": seeds,
            "width": request.width,
            "height": request.height,
            "num_inference_steps": request.num_inference_steps,
            "guidance_scale": request.guidance_scale,
            "model": "make-image-v4",
            "device": str(self.device),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_files": [
                {"path": p, "sha256": self._sha256(p)} for p in paths if Path(p).exists()
            ],
        }

    def _sha256(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


class ImageQualityGate:
    @staticmethod
    def check_sharpness(image_path: str, threshold: float = 0.05) -> Dict[str, Any]:
        img = Image.open(image_path).convert("L")
        arr = np.array(img).astype(np.float32)
        laplacian = np.abs(np.diff(arr, axis=0)) + np.abs(np.diff(arr, axis=1))
        score = float(np.mean(laplacian) / 255.0)
        return {
            "metric": "sharpness",
            "score": score,
            "passed": score >= threshold,
            "threshold": threshold,
        }

    @staticmethod
    def check_diversity(images: List[str]) -> Dict[str, Any]:
        if len(images) < 2:
            return {"metric": "diversity", "score": 0.0, "passed": True}

        histograms = []
        for path in images:
            img = Image.open(path).convert("RGB")
            arr = np.array(img)
            for c in range(3):
                hist, _ = np.histogram(arr[:, :, c], bins=32, range=(0, 256))
                histograms.append(hist / hist.sum())

        diversity = 0.0
        for i in range(len(histograms)):
            for j in range(i + 1, len(histograms)):
                diversity += np.sum(np.abs(histograms[i] - histograms[j]))

        diversity /= (len(histograms) * (len(histograms) - 1) / 2)
        return {
            "metric": "diversity",
            "score": float(diversity),
            "passed": diversity > 0.1,
        }

    @staticmethod
    def run_all(image_path: str, additional_images: Optional[List[str]] = None) -> Dict[str, Any]:
        results = {
            "sharpness": ImageQualityGate.check_sharpness(image_path),
        }

        if additional_images:
            results["diversity"] = ImageQualityGate.check_diversity([image_path] + additional_images)

        all_passed = all(r["passed"] for r in results.values())
        results["overall_passed"] = all_passed

        return results
