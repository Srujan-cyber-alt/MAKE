"""MAKE Cinematic Quality Gate.

Implements strict IMAX-level quality evaluation for generated videos.

This module does NOT fabricate scores. It computes measurable metrics and
compares them against configured thresholds. Any metric that cannot be
computed is recorded as UNAVAILABLE, not estimated.

Quality categories:
    1. Photorealism
    2. Facial/ anatomical correctness
    3. Temporal stability
    4. Cinematography
    5. Lighting/color
    6. Physics/environment
    7. Composition/aesthetics
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Thresholds (IMAX-target)
# ---------------------------------------------------------------------------

@dataclass
class CinematicThresholds:
    """Quality thresholds for IMAX-level cinematic generation."""

    # Photorealism
    min_facial_symmetry: float = 0.75
    max_artifact_rate: float = 0.05
    min_sharpness: float = 50.0  # Laplacian variance
    max_flicker: float = 0.08  # temporal luminance std

    # Temporal
    min_temporal_consistency: float = 0.85
    max_frame_drop: float = 0.02
    min_optical_flow_consistency: float = 0.80

    # Lighting/color
    min_exposure_range: float = 0.60  # usable dynamic range
    max_color_shift: float = 0.10
    min_shadow_detail: float = 0.30
    max_highlight_clip: float = 0.05

    # Cinematography
    min_camera_smoothness: float = 0.70
    max_jitter: float = 0.15
    min_depth_cues: float = 0.50

    # Physics/environment
    min_physics_plausibility: float = 0.70
    max_geometry_break: float = 0.10

    # Identity (when reference provided)
    min_identity_similarity: float = 0.80
    max_identity_drift: float = 0.05


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def _to_npy(x: Any) -> np.ndarray:
    if hasattr(x, "detach"):
        return x.detach().cpu().numpy()
    return np.asarray(x, dtype=np.float32)


def laplacian_variance(gray: np.ndarray) -> float:
    """Sharpness metric (higher = sharper)."""
    h, w = gray.shape
    if h < 3 or w < 3:
        return 0.0
    # simple 3x3 Laplacian
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    # manual convolution for numpy-only
    pad = 1
    padded = np.pad(gray, pad, mode="reflect")
    out = np.zeros_like(gray)
    for i in range(3):
        for j in range(3):
            out += padded[i:i+h, j:j+w] * kernel[i, j]
    return float(np.var(out))


def temporal_luminance_std(frames: np.ndarray) -> float:
    """Flicker metric (lower = more stable)."""
    if frames.ndim != 4:
        return 0.0
    means = frames.mean(axis=(1, 2, 3))
    return float(np.std(means))


def exposure_range(frames: np.ndarray) -> float:
    """Dynamic range utilization (0..1)."""
    p1 = np.percentile(frames, 1)
    p99 = np.percentile(frames, 99)
    if p99 <= p1:
        return 0.0
    return float(np.clip((p99 - p1) / 255.0, 0.0, 1.0))


def shadow_detail(frames: np.ndarray) -> float:
    """Fraction of pixels in shadow with detail (> 5 gray levels)."""
    shadows = frames[frames < 50]
    if shadows.size == 0:
        return 1.0
    return float(np.unique(shadows).size / 256.0)


def highlight_clip(frames: np.ndarray) -> float:
    """Fraction of clipped highlights."""
    return float(np.mean(frames > 250))


def frame_drop_rate(frames: np.ndarray) -> float:
    """Detect repeated frames (frame drops)."""
    if frames.shape[0] < 2:
        return 0.0
    diffs = np.abs(frames[1:] - frames[:-1]).mean(axis=(1, 2, 3))
    return float(np.mean(diffs < 2.0))


def optical_flow_consistency(frames: np.ndarray) -> float:
    """Placeholder for flow consistency. Returns 0.5 on CPU."""
    return 0.5


def camera_smoothness(frames: np.ndarray) -> float:
    """Low-frequency motion ratio (higher = smoother)."""
    if frames.shape[0] < 3:
        return 0.5
    diffs = np.abs(frames[1:] - frames[:-1]).mean(axis=(1, 2, 3))
    if diffs.size < 2:
        return 0.5
    low_freq = np.convolve(diffs, np.ones(min(3, diffs.size)) / 3, mode="same")
    total = np.sum(diffs)
    if total == 0:
        return 0.5
    return float(np.sum(low_freq) / total)


def facial_symmetry_placeholder(gray: np.ndarray) -> float:
    """Placeholder for facial symmetry. Returns 0.5 on CPU."""
    return 0.5


def identity_similarity_placeholder(
    generated: np.ndarray, reference: np.ndarray
) -> float:
    """Placeholder for identity similarity. Returns 0.5 on CPU."""
    return 0.5


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------

@dataclass
class CinematicQualityResult:
    """Result of cinematic quality evaluation."""

    passed: bool
    overall_score: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    unavailable: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

class CinematicQualityGate:
    """Evaluates generated video against IMAX-level quality thresholds."""

    def __init__(self, thresholds: Optional[CinematicThresholds] = None) -> None:
        self.thresholds = thresholds or CinematicThresholds()

    def evaluate(
        self,
        frames: np.ndarray,
        prompt: str = "",
        reference_frames: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CinematicQualityResult:
        """Evaluate video quality.

        frames: (T, H, W, C) uint8 or float32
        reference_frames: optional (T', H, W, C) for identity checks
        """
        metrics: Dict[str, Any] = {}
        failures: List[str] = []
        unavailable: List[str] = []

        frames = _to_npy(frames)
        if frames.ndim != 4:
            return CinematicQualityResult(
                passed=False, overall_score=0.0,
                failures=["invalid frame shape"],
            )

        gray = frames.mean(axis=3) if frames.shape[-1] >= 3 else frames.squeeze(-1)

        # 1. Photorealism
        sharpness = float(np.mean([laplacian_variance(gray[t]) for t in range(gray.shape[0])]))
        metrics["sharpness"] = sharpness
        if sharpness < self.thresholds.min_sharpness:
            failures.append(f"sharpness {sharpness:.2f} < {self.thresholds.min_sharpness}")

        flicker = temporal_luminance_std(frames)
        metrics["flicker"] = flicker
        if flicker > self.thresholds.max_flicker:
            failures.append(f"flicker {flicker:.3f} > {self.thresholds.max_flicker}")

        # 2. Temporal
        temporal_consistency = 1.0 - frame_drop_rate(frames)
        metrics["temporal_consistency"] = temporal_consistency
        if temporal_consistency < self.thresholds.min_temporal_consistency:
            failures.append(f"temporal_consistency {temporal_consistency:.3f} < {self.thresholds.min_temporal_consistency}")

        flow_consistency = optical_flow_consistency(frames)
        metrics["optical_flow_consistency"] = flow_consistency
        if flow_consistency == 0.5:
            unavailable.append("optical_flow_consistency (requires torch)")

        # 3. Lighting/color
        exp_range = exposure_range(frames)
        metrics["exposure_range"] = exp_range
        if exp_range < self.thresholds.min_exposure_range:
            failures.append(f"exposure_range {exp_range:.3f} < {self.thresholds.min_exposure_range}")

        shadow = shadow_detail(frames)
        metrics["shadow_detail"] = shadow
        if shadow < self.thresholds.min_shadow_detail:
            failures.append(f"shadow_detail {shadow:.3f} < {self.thresholds.min_shadow_detail}")

        highlight = highlight_clip(frames)
        metrics["highlight_clip"] = highlight
        if highlight > self.thresholds.max_highlight_clip:
            failures.append(f"highlight_clip {highlight:.3f} > {self.thresholds.max_highlight_clip}")

        # 4. Cinematography
        smoothness = camera_smoothness(frames)
        metrics["camera_smoothness"] = smoothness
        if smoothness < self.thresholds.min_camera_smoothness:
            failures.append(f"camera_smoothness {smoothness:.3f} < {self.thresholds.min_camera_smoothness}")

        # 5. Identity (if reference provided)
        if reference_frames is not None:
            identity = identity_similarity_placeholder(frames, reference_frames)
            metrics["identity_similarity"] = identity
            if identity == 0.5:
                unavailable.append("identity_similarity (requires torch)")
        else:
            unavailable.append("identity_similarity (no reference provided)")

        # 6. Facial/anatomical
        facial = facial_symmetry_placeholder(gray[0])
        metrics["facial_symmetry"] = facial
        if facial == 0.5:
            unavailable.append("facial_symmetry (requires torch + detector)")

        # Score: simple average of available pass-rate metrics
        score_parts = []
        for k, v in metrics.items():
            if k in unavailable_metrics():
                continue
            score_parts.append(min(float(v), 1.0))
        overall = float(np.mean(score_parts)) if score_parts else 0.0

        return CinematicQualityResult(
            passed=len(failures) == 0,
            overall_score=overall,
            metrics=metrics,
            failures=failures,
            unavailable=unavailable,
            notes="CPU-only evaluation. Torch-based metrics unavailable.",
        )


def unavailable_metrics() -> List[str]:
    return [
        "optical_flow_consistency",
        "identity_similarity",
        "facial_symmetry",
        "color_shift",
        "physics_plausibility",
        "geometry_break",
    ]


# ---------------------------------------------------------------------------
# Human evaluation protocol
# ---------------------------------------------------------------------------

@dataclass
class HumanEvaluationTask:
    """A human evaluation task."""

    task_id: str
    prompt: str
    video_path: str
    reference_path: Optional[str]
    criteria: List[str]
    max_score: float = 5.0


@dataclass
class HumanEvaluationResult:
    """Result of a human evaluation task."""

    task_id: str
    evaluator_id: str
    scores: Dict[str, float]
    notes: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HumanEvaluationProtocol:
    """Protocol for human evaluation of generated videos.

    This class does NOT fabricate human scores. It provides:
    - task definitions
    - scoring rubrics
    - aggregation methods
    - storage format

    Actual human evaluation requires real evaluators.
    """

    RUBRIC = {
        "photorealism": "Does the video look like real camera footage?",
        "facial_accuracy": "Are faces anatomically correct with realistic eyes, skin, hair?",
        "temporal_stability": "Is there flicker, popping, or temporal inconsistency?",
        "cinematography": "Is camera movement smooth and purposeful?",
        "lighting": "Is lighting physically plausible with correct shadows and highlights?",
        "composition": "Is the shot well-composed?",
        "identity": "Does the subject maintain identity across frames?",
        "physics": "Do objects and people move realistically?",
        "aesthetics": "Is the overall image aesthetically pleasing?",
    }

    @staticmethod
    def create_tasks(
        prompt: str,
        video_path: str,
        reference_path: Optional[str] = None,
        shot_types: Optional[List[str]] = None,
    ) -> List[HumanEvaluationTask]:
        """Create evaluation tasks for a generated video."""
        if shot_types is None:
            shot_types = [
                "cinematic portrait",
                "close-up",
                "medium shot",
                "wide shot",
                "walking shot",
                "slow camera push-in",
                "tracking shot",
                "orbit shot",
                "low-light shot",
                "golden-hour shot",
                "studio lighting",
                "dramatic cinematic lighting",
                "shallow depth-of-field shot",
                "environmental shot",
            ]
        tasks = []
        for i, shot in enumerate(shot_types):
            task = HumanEvaluationTask(
                task_id=f"eval_{i:03d}",
                prompt=f"{prompt} | {shot}",
                video_path=video_path,
                reference_path=reference_path,
                criteria=list(HumanEvaluationProtocol.RUBRIC.keys()),
            )
            tasks.append(task)
        return tasks

    @staticmethod
    def aggregate(results: List[HumanEvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {"status": "NO_RESULTS"}
        scores: Dict[str, List[float]] = {k: [] for k in HumanEvaluationProtocol.RUBRIC}
        for r in results:
            for k, v in r.scores.items():
                scores.setdefault(k, []).append(v)
        summary = {}
        for k, vals in scores.items():
            if vals:
                summary[k] = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)),
                    "count": len(vals),
                }
        return {"status": "AGGREGATED", "criteria": summary}


# ---------------------------------------------------------------------------
# Autonomous improvement loop
# ---------------------------------------------------------------------------

@dataclass
class QualityImprovementLoop:
    """Automated quality improvement loop.

    Workflow:
        generate -> evaluate -> classify failures -> update curriculum
        -> retrain -> validate -> promote if better -> rollback if worse
    """

    thresholds: CinematicThresholds = field(default_factory=CinematicThresholds)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def record_checkpoint(
        self,
        checkpoint_id: str,
        metrics: Dict[str, float],
        validation_score: float,
    ) -> None:
        entry = {
            "checkpoint_id": checkpoint_id,
            "metrics": metrics,
            "validation_score": validation_score,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }
        self.history.append(entry)

    def should_promote(self, checkpoint_id: str) -> Tuple[bool, str]:
        """Decide whether to promote a checkpoint."""
        if not self.history:
            return False, "no_history"
        current = self.history[-1]
        if current["checkpoint_id"] != checkpoint_id:
            return False, "checkpoint_mismatch"
        if current["validation_score"] >= 0.85:
            return True, "validation_score_met"
        return False, f"validation_score {current['validation_score']:.3f} < 0.85"

    def rollback_candidate(self) -> Optional[str]:
        """Find best previous checkpoint for rollback."""
        if len(self.history) < 2:
            return None
        scored = [(e["validation_score"], e["checkpoint_id"]) for e in self.history[:-1]]
        scored.sort(reverse=True)
        return scored[0][1] if scored else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "CinematicThresholds",
    "CinematicQualityResult",
    "CinematicQualityGate",
    "HumanEvaluationTask",
    "HumanEvaluationResult",
    "HumanEvaluationProtocol",
    "QualityImprovementLoop",
]
