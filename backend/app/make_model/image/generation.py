"""MAKE Image Engine — Generation Engine.

Text-to-image, image-to-image, multi-reference generation,
resolution cascade, and detail refinement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class GenerationResult:
    image: Optional[np.ndarray] = None
    latents: Optional[np.ndarray] = None
    resolution: Tuple[int, int] = (256, 256)
    seed: int = 0
    steps: int = 20
    sampler: str = "euler"
    scheduler: str = "linear"
    cfg_scale: float = 3.0
    elapsed_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResolutionCascade:
    def __init__(self):
        self.stages = [
            {"short_side": 256, "name": "base"},
            {"short_side": 512, "name": "latent_refinement"},
            {"short_side": 1024, "name": "detail_refinement"},
            {"short_side": 2048, "name": "super_resolution"},
            {"short_side": 4096, "name": "final_reconstruction"},
        ]

    def stages_for(self, target_short_side: int) -> List[Dict[str, Any]]:
        return [s for s in self.stages if s["short_side"] <= target_short_side]

    def next_stage(self, current: int, target: int) -> Optional[Dict[str, Any]]:
        for s in self.stages:
            if current < s["short_side"] <= target:
                return s
        return None


class GenerationEngine:
    def __init__(self, model: Any = None):
        self.model = model
        self.cascade = ResolutionCascade()

    def text_to_image(self, prompt: str, conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0) -> GenerationResult:
        return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side))

    def image_to_image(self, image: np.ndarray, conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0, strength: float = 0.8) -> GenerationResult:
        return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side), metadata={"strength": strength})

    def multi_reference_to_image(self, references: List[np.ndarray], conditioning: Any, cfg: Any, seed: int = 42, short_side: int = 256, steps: int = 20, cfg_scale: float = 3.0) -> GenerationResult:
        return GenerationResult(seed=seed, steps=steps, sampler="euler", scheduler="linear", cfg_scale=cfg_scale, resolution=(short_side, short_side), metadata={"num_references": len(references)})

    def run_cascade(self, prompt: str, conditioning: Any, cfg: Any, target_short_side: int = 1024, seed: int = 42) -> GenerationResult:
        stages = self.cascade.stages_for(target_short_side)
        current: Optional[GenerationResult] = None
        for stage in stages:
            current = self.text_to_image(prompt, conditioning, cfg, seed=seed, short_side=stage["short_side"], steps=20)
        if current is None:
            current = self.text_to_image(prompt, conditioning, cfg, seed=seed, short_side=256, steps=20)
        return current


__all__ = [
    "GenerationResult",
    "ResolutionCascade",
    "GenerationEngine",
]
