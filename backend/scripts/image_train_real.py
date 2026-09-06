#!/usr/bin/env python3
"""MAKE Image Engine — Real Image Training Launcher.

Trains the MAKE-native image foundation model on real images.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


def load_image(path: str, size: int = 256) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)


def load_dataset(dataset_dir: str, size: int = 256, max_samples: int = 100) -> List[np.ndarray]:
    images = []
    for fname in os.listdir(dataset_dir):
        if fname.endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(dataset_dir, fname)
            try:
                img = load_image(path, size)
                images.append(img)
                if len(images) >= max_samples:
                    break
            except Exception:
                continue
    return images


def main():
    parser = argparse.ArgumentParser(description="MAKE Image Real Training Launcher")
    parser.add_argument("--dataset-dir", type=str, default="./dataset", help="Dataset directory")
    parser.add_argument("--preset", type=str, default="TINY", help="Model preset")
    parser.add_argument("--steps", type=int, default=100, help="Training steps")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--output-dir", type=str, default="./outputs", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--image-size", type=int, default=64, help="Training image size")
    parser.add_argument("--generate", action="store_true", help="Generate sample after training")
    parser.add_argument("--prompt", type=str, default="a cinematic portrait", help="Generation prompt")
    parser.add_argument("--inference-steps", type=int, default=10, help="Inference steps")
    args = parser.parse_args()

    np.random.seed(args.seed)

    from app.make_model.image.arch import ImageConfig, ImageFoundationModel
    from app.make_model.image.training import ImageTrainingConfig, ImageTrainer
    from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[MAKE Image] Loading dataset from {args.dataset_dir}")
    images = load_dataset(args.dataset_dir, size=args.image_size, max_samples=args.steps)
    if not images:
        print("[MAKE Image] No images found, using synthetic data")
        images = [np.random.randn(3, args.image_size, args.image_size).astype(np.float32) for _ in range(args.steps)]
    print(f"[MAKE Image] Loaded {len(images)} images")

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

    print(f"[MAKE Image] Training for {args.steps} steps on real images")
    t0 = time.time()
    losses = []
    for step, img in enumerate(images[:args.steps]):
        batch = {
            "latents": img[None],
            "text_tok": np.random.randint(0, cfg.text_vocab_size, size=(1, 16), dtype=np.int64),
        }
        result = trainer.train_step(batch)
        losses.append(result["loss"])
        if (step + 1) % 10 == 0:
            avg_loss = float(np.mean(losses[-10:]))
            print(f"[MAKE Image] Step {step+1}/{args.steps} | loss={avg_loss:.6f}")

    training_time = time.time() - t0
    print(f"[MAKE Image] Training completed in {training_time:.2f}s")

    ckpt_path = os.path.join(args.output_dir, f"{cfg.name}_real_final.ckpt.npz")
    trainer.save_checkpoint(ckpt_path)
    print(f"[MAKE Image] Checkpoint saved to {ckpt_path}")

    meta = {
        "model_name": cfg.name,
        "parameter_count": model.parameter_count(),
        "training_steps": args.steps,
        "training_time_seconds": training_time,
        "final_loss": float(np.mean(losses[-10:])) if losses else 0.0,
        "dataset_samples": len(images),
        "dataset_source": args.dataset_dir,
        "checkpoint_path": ckpt_path,
        "seed": args.seed,
        "preset": args.preset,
        "image_size": args.image_size,
    }
    meta_path = os.path.join(args.output_dir, f"{cfg.name}_real_final.meta.json")
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
            short_side=args.image_size * 2,
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
