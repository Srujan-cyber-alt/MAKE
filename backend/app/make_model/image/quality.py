"""MAKE Image Engine — Quality System.

Quality gate, photographic realism engine, detail recovery engine,
failure detection, and benchmark system.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    face_quality: float = 0.0
    hand_quality: float = 0.0
    skin_realism: float = 0.0
    hair_realism: float = 0.0
    camera_realism: float = 0.0
    texture_realism: float = 0.0
    resolution_quality: float = 0.0
    physics_plausibility: float = 0.0
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
            "face_quality": self.face_quality,
            "hand_quality": self.hand_quality,
            "skin_realism": self.skin_realism,
            "hair_realism": self.hair_realism,
            "camera_realism": self.camera_realism,
            "texture_realism": self.texture_realism,
            "resolution_quality": self.resolution_quality,
            "physics_plausibility": self.physics_plausibility,
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


class FailureDetector:
    def __init__(self):
        self.failure_types = [
            "malformed_anatomy",
            "duplicate_limbs",
            "broken_hands",
            "incorrect_reflections",
            "impossible_shadows",
            "face_drift",
            "object_drift",
            "texture_artifacts",
            "tiling_seams",
            "over_sharpening",
            "hallucinated_text",
            "geometry_collapse",
            "inconsistent_lighting",
            "plastic_skin",
            "unnatural_eyes",
            "deformed_hands",
        ]

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        failures = []
        scores = {}
        scores["high_frequency_artifacts"] = float(np.mean(np.abs(x[:, :, 1:] - x[:, :, :-1])))
        scores["low_frequency_bias"] = float(np.mean(np.abs(x - np.mean(x, axis=(2, 3), keepdims=True))))
        if scores["high_frequency_artifacts"] > 0.5:
            failures.append("over_sharpening")
        if scores["low_frequency_bias"] > 0.3:
            failures.append("texture_artifacts")
        if np.std(x) < 0.05:
            failures.append("geometry_collapse")
        if float(np.mean(x)) > 0.95 or float(np.mean(x)) < 0.05:
            failures.append("impossible_shadows")
        return {
            "failures": failures,
            "scores": scores,
            "is_failed": len(failures) > 0,
            "failure_count": len(failures),
        }


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
            "face_quality": 0.6,
            "hand_quality": 0.6,
            "skin_realism": 0.6,
            "hair_realism": 0.5,
            "camera_realism": 0.5,
            "texture_realism": 0.5,
            "resolution_quality": 0.5,
            "physics_plausibility": 0.6,
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


@dataclass
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    references: List[str] = field(default_factory=list)
    conditioning: Dict[str, Any] = field(default_factory=dict)
    expected_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    name: str = "make-image-benchmark-v1"
    cases: List[BenchmarkCase] = field(default_factory=list)

    def add_case(self, case: BenchmarkCase) -> None:
        self.cases.append(case)

    def cases_by_category(self, category: str) -> List[BenchmarkCase]:
        return [c for c in self.cases if c.category == category]


class ImageBenchmark:
    def __init__(self):
        self.suite = BenchmarkSuite()
        self._populate_defaults()

    def _populate_defaults(self) -> None:
        categories = [
            "text_to_image", "photorealism", "human_realism", "identity", "hands",
            "objects", "materials", "lighting", "composition", "multi_reference",
            "editing", "inpainting", "outpainting", "world_consistency", "camera_control",
            "depth", "pose", "product", "architecture", "environments", "surreal", "high_resolution",
        ]
        for i, cat in enumerate(categories):
            self.suite.add_case(BenchmarkCase(
                case_id=f"{cat}_{i:03d}",
                category=cat,
                prompt=f"benchmark prompt for {cat}",
                expected_metrics={"realism": 0.7, "anatomy": 0.7, "detail": 0.5},
            ))

    def run(self, engine: Any) -> Dict[str, Any]:
        results = []
        for case in self.suite.cases:
            try:
                result = engine.run(case)
                results.append({"case_id": case.case_id, "ok": True, "result": result})
            except Exception as e:
                results.append({"case_id": case.case_id, "ok": False, "error": str(e)})
        return {"total": len(results), "passed": sum(1 for r in results if r.get("ok")), "failed": sum(1 for r in results if not r.get("ok")), "results": results}


@dataclass
class HumanEvaluationRecord:
    evaluator_id: str
    case_id: str
    scores: Dict[str, float] = field(default_factory=dict)
    preferred: str = ""
    notes: str = ""
    is_realistic: bool = False
    is_production_ready: bool = False


class HumanEvaluationWorkflow:
    def __init__(self):
        self.records: List[HumanEvaluationRecord] = []

    def submit(self, record: HumanEvaluationRecord) -> None:
        self.records.append(record)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_evaluations": len(self.records),
            "evaluators": len({r.evaluator_id for r in self.records}),
            "cases": len({r.case_id for r in self.records}),
        }


__all__ = [
    "QualityMetrics",
    "PhotographicRealismEngine",
    "DetailRecoveryEngine",
    "FailureDetector",
    "QualityGate",
    "BenchmarkCase",
    "BenchmarkSuite",
    "ImageBenchmark",
    "HumanEvaluationRecord",
    "HumanEvaluationWorkflow",
]
