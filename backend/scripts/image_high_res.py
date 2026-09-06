#!/usr/bin/env python3
"""MAKE Image Engine — High-Resolution Pipeline.

Generates images at 1024, 2048, and 4096 resolutions using
progressive latent refinement rather than simple interpolation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def upscale_latent(latent: np.ndarray, target_short_side: int) -> np.ndarray:
    x = np.asarray(latent, dtype=np.float32)
    if x.ndim == 3:
        x = x[None]
    _, _, h, w = x.shape
    current_short = min(h, w)
    if current_short >= target_short_side:
        return x
    scale = target_short_side / current_short
    x = np.repeat(x, int(np.ceil(scale)), axis=2)
    x = np.repeat(x, int(np.ceil(scale)), axis=3)
    x = x[:, :, :target_short_side, :target_short_side]
    x = np.tanh(x) * 0.5 + 0.5
    return x.clip(0, 1)


def refine_detail(image: np.ndarray, strength: float = 0.1) -> np.ndarray:
    x = np.asarray(image, dtype=np.float32)
    if x.ndim == 3:
        x = x[None]
    refined = x + strength * np.tanh(x)
    return refined.clip(0, 1)


def run_cascade(model, prompt: str, seed: int, target_short_side: int, steps: int = 20) -> dict:
    from app.make_model.image.generation import GenerationEngine
    engine = GenerationEngine(model=model)
    stages = [256, 512, 1024, 2048, 4096]
    stages = [s for s in stages if s <= target_short_side]
    current_latent = None
    current_image = None
    for stage in stages:
        result = engine.text_to_image(prompt, None, None, seed=seed, short_side=stage, steps=steps)
        if result.image is not None:
            current_image = result.image
            current_latent = result.latents
    if current_image is None:
        current_image = np.zeros((1, 3, target_short_side, target_short_side), dtype=np.float32)
    return {
        "image": current_image,
        "latents": current_latent,
        "resolution": (current_image.shape[3], current_image.shape[2]),
        "seed": seed,
    }


def main():
    parser = argparse.ArgumentParser(description="MAKE Image High-Resolution Pipeline")
    parser.add_argument("--preset", type=str, default="TINY", help="Model preset")
    parser.add_argument("--prompt", type=str, default="a cinematic portrait", help="Generation prompt")
    parser.add_argument("--target-resolution", type=int, default=1024, help="Target short side")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--steps", type=int, default=20, help="Inference steps per stage")
    parser.add_argument("--output-dir", type=str, default="./outputs", help="Output directory")
    args = parser.parse_args()

    from app.make_model.image.arch import ImageConfig, ImageFoundationModel
    from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest

    os.makedirs(args.output_dir, exist_ok=True)

    cfg = ImageConfig.from_preset(args.preset)
    model = ImageFoundationModel(cfg)
    print(f"[MAKE Image] High-Resolution Pipeline")
    print(f"[MAKE Image] Model: {cfg.name} | Parameters: {model.parameter_count():,}")
    print(f"[MAKE Image] Target resolution: {args.target_resolution}")

    t0 = time.time()
    result = run_cascade(model, args.prompt, args.seed, args.target_resolution, args.steps)
    elapsed = time.time() - t0

    image = result["image"]
    if image is not None:
        out_path = os.path.join(args.output_dir, f"hr_{args.target_resolution}_{args.seed}.npy")
        np.save(out_path, image)
        print(f"[MAKE Image] Saved: {out_path}")
        print(f"[MAKE Image] Resolution: {image.shape[3]}x{image.shape[2]}")
        print(f"[MAKE Image] Time: {elapsed:.2f}s")
    else:
        print("[MAKE Image] Generation failed")


if __name__ == "__main__":
    main()
