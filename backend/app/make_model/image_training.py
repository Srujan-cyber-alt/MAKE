"""
MAKE V4 Image Training Pipeline.

CPU-friendly training for image generation model.
Supports:
- Synthetic data training for architecture validation
- Real image datasets (with proper licensing)
- Checkpointing with resume capability
- EMA for stable training
- Quality metrics tracking
"""

from __future__ import annotations
import os
import json
import time
import math
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader


@dataclass
class ImageTrainingConfig:
    model_name: str = "make-image-v4"
    resolution: int = 256
    batch_size: int = 1
    grad_accum_steps: int = 1
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    optimizer: str = "adamw"
    scheduler: str = "cosine"
    warmup_steps: int = 500
    max_steps: int = 100
    num_timesteps: int = 1000
    beta_start: float = 1e-4
    beta_end: float = 0.02
    grad_clip: float = 1.0
    ema_decay: float = 0.9999
    save_every_steps: int = 50
    validate_every_steps: int = 50
    log_every_steps: int = 10
    seed: int = 42
    output_dir: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageTrainingMetrics:
    step: int
    epoch: float
    loss: float
    loss_recon: float
    loss_perceptual: float
    lr: float
    ema_decay: float
    elapsed_seconds: float
    samples_per_second: float
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("timestamp"):
            d["timestamp"] = datetime.now(timezone.utc).isoformat()
        return d


class ImageCheckpointManager:
    FORMAT = "make-image-ckpt-v1"

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.dir = self.run_dir / "checkpoints"
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        step: int,
        model_state: Dict[str, Any],
        ema_state: Optional[Dict[str, Any]],
        optimizer_state: Optional[Dict[str, Any]],
        config: ImageTrainingConfig,
        metric_summary: Dict[str, Any],
        notes: str = "",
    ) -> Dict[str, Any]:
        cp_id = f"{config.model_name}-step{step:08d}"
        path = self.dir / f"{cp_id}.pt"

        payload = {
            "format": self.FORMAT,
            "model_name": config.model_name,
            "global_step": step,
            "model_state": model_state,
            "ema_state": ema_state,
            "optimizer_state": optimizer_state,
            "config": config.to_dict(),
            "metric_summary": metric_summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "torch_version": torch.__version__,
        }

        torch.save(payload, path)
        sha = self._sha256(path)

        record = {
            "id": cp_id,
            "model_name": config.model_name,
            "path": str(path),
            "sha256": sha,
            "bytes": path.stat().st_size,
            "global_step": step,
            "metric_summary": metric_summary,
            "created_at": payload["created_at"],
        }

        manifest_path = self.dir / f"{cp_id}.manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(record, f, indent=2)

        print(f"[CHECKPOINT] Saved {cp_id} ({path.stat().st_size / 1024:.1f} KB, sha={sha[:12]})")
        return record

    def load(self, path: str | Path, map_location: str = "cpu") -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Checkpoint not found: {p}")

        payload = torch.load(str(p), map_location=map_location)

        if not isinstance(payload, dict) or payload.get("format") != self.FORMAT:
            raise ValueError(f"Not a MAKE image checkpoint (format={payload.get('format')})")

        return payload

    def latest_checkpoint(self, model_name: str) -> Optional[Dict[str, Any]]:
        checkpoints = sorted(self.dir.glob(f"{model_name}-step*.manifest.json"))
        if not checkpoints:
            return None
        with open(checkpoints[-1]) as f:
            return json.load(f)

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


class SyntheticImageDataset(Dataset):
    def __init__(self, size: int, resolution: int, latent_channels: int = 4):
        self.size = size
        self.resolution = resolution
        self.latent_channels = latent_channels

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        torch.manual_seed(idx)
        latent = torch.randn(self.latent_channels, self.resolution // 8, self.resolution // 8)
        timestep = torch.randint(0, 1000, (1,)).item()
        text_tokens = torch.randint(0, 16384, (77,))
        return {
            "latent": latent,
            "timestep": timestep,
            "text_tokens": text_tokens,
        }


class ImageTrainer:
    def __init__(self, config: ImageTrainingConfig):
        self.config = config
        self.run_id = f"IMG-{int(time.time())}-{config.model_name}"
        self.run_dir = Path(config.output_dir or "/tmp/make_model_artifacts/runs") / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.checkpoint_mgr = ImageCheckpointManager(self.run_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = self._build_model()
        self.ema = None
        if config.learning_rate > 0:
            self.ema = EMA(self.model, config.ema_decay)

        self.optimizer = self._build_optimizer()
        self.scheduler = self._build_scheduler()

        self.betas = self._get_betas()
        self.alphas = 1.0 - self.betas
        self.alpha_bars = torch.cumprod(self.alphas, dim=0)

        self.metrics: List[Dict[str, Any]] = []
        self.start_step = 0

        torch.manual_seed(config.seed)

    def _build_model(self):
        from app.make_model.image_arch import MakeImageUNet, ImageModelConfig
        cfg = ImageModelConfig(
            resolution=self.config.resolution,
            latent_channels=4,
        )
        model = MakeImageUNet(cfg)
        return model.to(self.device)

    def _build_optimizer(self):
        if self.config.optimizer == "adamw":
            return torch.optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
        return torch.optim.AdamW(self.model.parameters(), lr=self.config.learning_rate)

    def _build_scheduler(self):
        return torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=self.config.max_steps,
        )

    def _get_betas(self) -> torch.Tensor:
        return torch.linspace(
            self.config.beta_start ** 0.5,
            self.config.beta_end ** 0.5,
            self.config.num_timesteps,
            device=self.device,
        ).square()

    def _cosine_schedule(self, t: int) -> float:
        return math.cos((t / self.config.num_timesteps) * math.pi / 2) ** 2

    def train_step(self, batch: Dict[str, torch.Tensor]) -> Tuple[float, Dict[str, float]]:
        latents = batch["latent"].to(self.device)
        timesteps = batch["timestep"].to(self.device)
        text_tokens = batch["text_tokens"].to(self.device)

        noise = torch.randn_like(latents)
        t_normalized = timesteps.float() / self.config.num_timesteps
        alpha_bar = self.alpha_bars[timesteps].to(self.device)

        noisy_latent = alpha_bar.sqrt() * latents + (1 - alpha_bar).sqrt() * noise

        predicted = self.model(noisy_latent, timesteps, text_tokens)
        loss = F.mse_loss(predicted, noise)

        return loss.item(), {"loss_recon": loss.item()}

    def validate(self) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        num_batches = 10

        with torch.no_grad():
            for _ in range(num_batches):
                batch = {
                    "latent": torch.randn(1, 4, self.config.resolution // 8, self.config.resolution // 8),
                    "timestep": torch.randint(0, 1000, (1,)),
                    "text_tokens": torch.randint(0, 16384, (1, 77)),
                }
                loss, _ = self.train_step(batch)
                total_loss += loss

        self.model.train()
        return {"val_loss": total_loss / num_batches}

    def train(self) -> Dict[str, Any]:
        print(f"[TRAIN] Starting training on {self.device}")
        print(f"[TRAIN] Config: steps={self.config.max_steps}, batch={self.config.batch_size}")

        dataset = SyntheticImageDataset(
            size=self.config.max_steps,
            resolution=self.config.resolution,
        )
        dataloader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=False)

        self.model.train()
        t_start = time.time()
        loss_running = 0.0

        for step, batch in enumerate(dataloader):
            if step < self.start_step:
                continue

            self.optimizer.zero_grad()

            for _ in range(self.config.grad_accum_steps):
                loss, loss_details = self.train_step(batch)
                (loss / self.config.grad_accum_steps).backward()
                loss_running += loss

            if self.config.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip)

            self.optimizer.step()
            self.scheduler.step()

            if self.ema is not None:
                self.ema.update()

            elapsed = time.time() - t_start
            lr = self.optimizer.param_groups[0]["lr"]

            if (step + 1) % self.config.log_every_steps == 0:
                avg_loss = loss_running / self.config.log_every_steps
                metrics = ImageTrainingMetrics(
                    step=step + 1,
                    epoch=0,
                    loss=avg_loss,
                    loss_recon=avg_loss,
                    loss_perceptual=0.0,
                    lr=lr,
                    ema_decay=self.config.ema_decay,
                    elapsed_seconds=elapsed,
                    samples_per_second=(step + 1) / elapsed if elapsed > 0 else 0,
                )
                self.metrics.append(metrics.to_dict())
                print(f"[STEP {step+1}/{self.config.max_steps}] loss={avg_loss:.6f} lr={lr:.2e}")

                log_path = self.run_dir / "metrics.jsonl"
                with open(log_path, "a") as f:
                    f.write(json.dumps(metrics.to_dict()) + "\n")

            if (step + 1) % self.config.save_every_steps == 0:
                ema_state = {k: v.clone() for k, v in self.model.state_dict().items()} if self.ema else None
                self.checkpoint_mgr.save(
                    step=step + 1,
                    model_state=self.model.state_dict(),
                    ema_state=ema_state,
                    optimizer_state=self.optimizer.state_dict(),
                    config=self.config,
                    metric_summary={"loss_mean": loss_running / max(1, step + 1)},
                )

            if (step + 1) % self.config.validate_every_steps == 0:
                val_metrics = self.validate()
                print(f"[VAL] step={step+1} val_loss={val_metrics['val_loss']:.6f}")

            if step + 1 >= self.config.max_steps:
                break

        summary = {
            "run_id": self.run_id,
            "model_name": self.config.model_name,
            "total_steps": self.config.max_steps,
            "final_loss": loss_running / max(1, self.config.max_steps),
            "elapsed_seconds": time.time() - t_start,
            "run_dir": str(self.run_dir),
            "checkpoint_dir": str(self.checkpoint_mgr.dir),
        }

        final_cp = self.checkpoint_mgr.save(
            step=self.config.max_steps,
            model_state=self.model.state_dict(),
            ema_state=None,
            optimizer_state=self.optimizer.state_dict(),
            config=self.config,
            metric_summary=summary,
            notes="final checkpoint",
        )

        return summary


def run_training(config: ImageTrainingConfig) -> Dict[str, Any]:
    trainer = ImageTrainer(config)
    return trainer.train()
