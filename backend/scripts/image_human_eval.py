#!/usr/bin/env python3
"""MAKE Image Engine — Human Evaluation Package Generator.

Creates evaluation packages for human raters.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def generate_evaluation_set(output_dir: str, num_samples: int = 16) -> list:
    from app.make_model.image.arch import ImageConfig, ImageFoundationModel
    from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest
    from app.make_model.image.quality import QualityGate, QualityMetrics, PhotographicRealismEngine

    os.makedirs(output_dir, exist_ok=True)
    cfg = ImageConfig.from_preset("TINY")
    model = ImageFoundationModel(cfg)
    engine = ImageInferenceEngine()
    quality_engine = PhotographicRealismEngine()
    gate = QualityGate()

    categories = [
        "cinematic_portrait",
        "full_body_human",
        "human_environment",
        "architecture",
        "product",
        "night_scene",
        "daylight_scene",
        "low_light",
        "multi_person",
        "hands_pose",
        "material_control",
        "camera_control",
        "lighting_control",
        "identity_consistency",
        "editing_preservation",
        "high_resolution",
    ]

    samples = []
    for i in range(num_samples):
        category = categories[i % len(categories)]
        prompt = f"benchmark: {category}"
        seed = 42 + i
        req = ImageInferenceRequest(
            prompt=prompt,
            model_name=cfg.name,
            checkpoint_id="default",
            seed=seed,
            short_side=64,
            num_inference_steps=2,
        )
        result = engine.run(req)
        image = np.load(result.output_path) if result.output_path and os.path.exists(result.output_path) else None
        metrics = QualityMetrics()
        if image is not None:
            assessed = quality_engine.assess(image)
            metrics = assessed
        quality_result = gate.evaluate(metrics)
        sample = {
            "case_id": f"{category}_{i:03d}",
            "category": category,
            "prompt": prompt,
            "seed": seed,
            "resolution": result.resolution,
            "output_path": result.output_path,
            "provenance_path": result.output_path + ".provenance.json" if result.output_path else None,
            "quality_metrics": metrics.to_dict(),
            "quality_passed": quality_result["passed"],
            "quality_failures": quality_result["failures"],
        }
        samples.append(sample)
        with open(os.path.join(output_dir, f"sample_{i:03d}_eval.json"), "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2)
    return samples


def main():
    parser = argparse.ArgumentParser(description="MAKE Image Human Evaluation Package Generator")
    parser.add_argument("--output-dir", type=str, default="./outputs/evaluations", help="Output directory")
    parser.add_argument("--samples", type=int, default=16, help="Number of samples")
    args = parser.parse_args()

    samples = generate_evaluation_set(args.output_dir, args.samples)
    summary = {
        "total_samples": len(samples),
        "categories": list(set(s["category"] for s in samples)),
        "passed_quality": sum(1 for s in samples if s["quality_passed"]),
        "failed_quality": sum(1 for s in samples if not s["quality_passed"]),
        "samples": samples,
    }
    with open(os.path.join(args.output_dir, "evaluation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[MAKE Image] Generated {len(samples)} evaluation samples")
    print(f"[MAKE Image] Quality passed: {summary['passed_quality']}/{summary['total_samples']}")
    print(f"[MAKE Image] Output: {args.output_dir}")


if __name__ == "__main__":
    main()
