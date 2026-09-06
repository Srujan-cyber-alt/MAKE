"""MAKE Image Engine — Quality System.

Quality gate, photographic realism engine, detail recovery engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class QualityMetrics:
    realism: float = 0.0
    anatomy: float = 0.0
    identity_consistency: float = 0.0
    object_consistency: float = 0.0
    material_realism: float = 0.0
    lighting: float = 0.0
    shadows: float = 0.0
    reflections: float = 0.0
    depth: float = 0.0
    perspective: float = 0.0
    composition: float = 0.0
    text_rendering: float = 0.0
    detail: float = 0.0
    artifacts: float = 0.0
    world_consistency: float = 0.0
    edit_fidelity: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "realism": self.realism,
            "anatomy": self.anatomy,
            "identity_consistency": self.identity_consistency,
            "object_consistency": self.object_consistency,
            "material_realism": self.material_realism,
            "lighting": self.lighting,
            "shadows": self.shadows,
            "reflections": self.reflections,
            "depth": self.depth,
            "perspective": self.perspective,
            "composition": self.composition,
            "text_rendering": self.text_rendering,
            "detail": self.detail,
            "artifacts": self.artifacts,
            "world_consistency": self.world_consistency,
            "edit_fidelity": self.edit_fidelity,
            "overall": self.overall,
        }


class PhotographicRealismEngine:
    def __init__(self):
        pass

    def assess(self, image: np.ndarray, reference: Optional[np.ndarray] = None) -> QualityMetrics:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        metrics = QualityMetrics()
        metrics.detail = float(np.mean(np.abs(x[:, :, 1:] - x[:, :, :-1])))
        metrics.lighting = float(np.mean(x))
        metrics.shadows = float(np.min(x))
        metrics.reflections = float(np.max(x))
        metrics.depth = float(np.std(x))
        metrics.perspective = 0.5
        metrics.composition = 0.5
        metrics.material_realism = 0.5
        metrics.artifacts = float(np.mean(np.abs(x - np.mean(x, axis=(2, 3), keepdims=True))))
        metrics.realism = 1.0 - metrics.artifacts
        metrics.overall = float(np.mean([metrics.realism, metrics.detail, metrics.lighting, metrics.depth]))
        return metrics


class DetailRecoveryEngine:
    def __init__(self):
        pass

    def recover(self, image: np.ndarray, target_short_side: int = 1024) -> np.ndarray:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        scale = target_short_side / max(x.shape[2], x.shape[3])
        if scale > 1.0:
            x = np.repeat(x, int(scale), axis=2)
            x = np.repeat(x, int(scale), axis=3)
            x = x + 0.05 * np.tanh(x)
        return x.clip(0, 1)


class QualityGate:
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or {
            "realism": 0.7,
            "anatomy": 0.7,
            "identity_consistency": 0.7,
            "object_consistency": 0.7,
            "material_realism": 0.6,
            "lighting": 0.6,
            "shadows": 0.6,
            "reflections": 0.6,
            "depth": 0.6,
            "perspective": 0.6,
            "composition": 0.6,
            "detail": 0.5,
            "artifacts": 0.3,
            "world_consistency": 0.7,
            "edit_fidelity": 0.7,
        }

    def evaluate(self, metrics: QualityMetrics) -> Dict[str, Any]:
        d = metrics.to_dict()
        passed = True
        failures = []
        lower_is_better = {"artifacts"}
        for key, threshold in self.thresholds.items():
            value = d.get(key, 0.0)
            if key in lower_is_better:
                if value > threshold:
                    passed = False
                    failures.append(key)
            else:
                if value < threshold:
                    passed = False
                    failures.append(key)
        return {"passed": passed, "failures": failures, "metrics": d, "thresholds": self.thresholds}


__all__ = [
    "QualityMetrics",
    "PhotographicRealismEngine",
    "DetailRecoveryEngine",
    "QualityGate",
]
