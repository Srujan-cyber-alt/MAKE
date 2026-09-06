#!/usr/bin/env python3
"""MAKE Image Engine — Training Launcher.

Trains the MAKE-native image foundation model on a small dataset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="MAKE Image Training Launcher")
    parser.add_argument("--preset", type=str, default="TINY", help="Model preset")
    parser.add_argument("--steps", type=int, default=50, help="Training steps")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--output-dir", type=str, default="./outputs", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--generate", action="store_true", help="Generate sample after training")
    parser.add_argument("--prompt", type=str, default="a cinematic portrait", help="Generation prompt")
    parser.add_argument("--short-side", type=int, default=64, help="Generation resolution")
    parser.add_argument("--inference-steps", type=int, default=10, help="Inference steps")
    args = parser.parse_args()

    np.random.seed(args.seed)

    from app.make_model.image.arch import ImageConfig, ImageFoundationModel
    from app.make_model.image.training import ImageTrainingConfig, ImageTrainer
    from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[MAKE Image] Initializing model with preset={args.preset}")
    cfg = ImageConfig.from_preset(args.preset)
    model = ImageFoundationModel(cfg)
    print(f"[MAKE Image] Model parameter count: {model.parameter_count():,}")

    train_cfg = ImageTrainingConfig(
        model_name=cfg.name,
        max_steps=args.steps,
        batch_size=args.batch_size,
        learning_rate=1e-4,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    trainer = ImageTrainer(train_cfg, model)

    print(f"[MAKE Image] Creating synthetic training dataset ({args.steps} samples)")
    dataset = []
    for i in range(args.steps):
        sample = {
            "latents": np.random.randn(args.batch_size, cfg.latent_channels, 32, 32).astype(np.float32),
            "text_tok": np.random.randint(0, cfg.text_vocab_size, size=(args.batch_size, 16), dtype=np.int64),
        }
        dataset.append(sample)

    print(f"[MAKE Image] Training for {args.steps} steps")
    t0 = time.time()
    losses = []
    for step, batch in enumerate(dataset):
        result = trainer.train_step(batch)
        losses.append(result["loss"])
        if (step + 1) % 10 == 0:
            avg_loss = float(np.mean(losses[-10:]))
            print(f"[MAKE Image] Step {step+1}/{args.steps} | loss={avg_loss:.6f}")

    training_time = time.time() - t0
    print(f"[MAKE Image] Training completed in {training_time:.2f}s")

    ckpt_path = os.path.join(args.output_dir, f"{cfg.name}_final.ckpt.npz")
    trainer.save_checkpoint(ckpt_path)
    print(f"[MAKE Image] Checkpoint saved to {ckpt_path}")

    meta = {
        "model_name": cfg.name,
        "parameter_count": model.parameter_count(),
        "training_steps": args.steps,
        "training_time_seconds": training_time,
        "final_loss": float(np.mean(losses[-10:])) if losses else 0.0,
        "checkpoint_path": ckpt_path,
        "seed": args.seed,
        "preset": args.preset,
    }
    meta_path = os.path.join(args.output_dir, f"{cfg.name}_final.meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[MAKE Image] Metadata saved to {meta_path}")

    if args.generate:
        print(f"[MAKE Image] Generating sample: prompt='{args.prompt}'")
        engine = ImageInferenceEngine()
        req = ImageInferenceRequest(
            prompt=args.prompt,
            model_name=cfg.name,
            checkpoint_id=os.path.basename(ckpt_path),
            seed=args.seed,
            short_side=args.short_side,
            num_inference_steps=args.inference_steps,
        )
        result = engine.run(req)
        if result.ok:
            print(f"[MAKE Image] Generated image saved to: {result.output_path}")
            print(f"[MAKE Image] Resolution: {result.resolution}")
            print(f"[MAKE Image] Inference time: {result.elapsed_seconds:.2f}s")
        else:
            print(f"[MAKE Image] Generation failed: {result.message}")

    print("[MAKE Image] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
