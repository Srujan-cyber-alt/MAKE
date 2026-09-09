"""
Weighted validation across all 8 continuity dimensions.

Each dimension receives a weight and a score in [0, 1].  The validator
produces an overall score and a list of issues to fix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.audio_continuity_engine import (
    AudioContinuityEngine,
    ContinuityType,
    CONTINUITY_TYPES,
)


DEFAULT_WEIGHTS: Dict[str, float] = {
    "voice": 0.25,
    "emotion": 0.20,
    "room": 0.15,
    "mic": 0.10,
    "background": 0.10,
    "spatial": 0.10,
    "loudness": 0.05,
    "acoustic": 0.05,
}


class ValidationLevel(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    FAIL = "FAIL"


@dataclass
class DimensionResult:
    dimension: str
    score: float
    weight: float
    issues: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "weighted_score": self.weighted_score,
            "issues": list(self.issues),
        }


@dataclass
class ValidationResult:
    level: ValidationLevel
    overall_score: float
    dimensions: List[DimensionResult]
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "overall_score": self.overall_score,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "issues": list(self.issues),
            "recommendations": list(self.recommendations),
        }


class ContinuityValidator:
    """Weighted validation across all 8 continuity dimensions."""

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)
        # Ensure all 8 dimensions have a weight.
        for ct in CONTINUITY_TYPES:
            self.weights.setdefault(ct, 0.0)

    def validate(self, engine: AudioContinuityEngine, expected: Optional[Dict[str, Any]] = None) -> ValidationResult:
        expected = expected or {}
        dimensions: List[DimensionResult] = []
        issues: List[str] = []
        recommendations: List[str] = []

        for ct in CONTINUITY_TYPES:
            ctype = ContinuityType(ct)
            state = engine.get_state(ctype)
            weight = self.weights.get(ct, 0.0)
            dim_issues: List[str] = []
            score = 1.0
            if state is None:
                score = 0.0
                dim_issues.append(f"Missing continuity state for {ct}")
                if ct in expected:
                    issues.append(f"{ct}: expected {expected[ct]}, got missing")
                    recommendations.append(f"Set {ct} continuity to {expected[ct]}")
            else:
                if ct in expected:
                    actual = state.value
                    if actual != expected[ct]:
                        score *= 0.5
                        dim_issues.append(f"Value mismatch: {actual} != {expected[ct]}")
                        issues.append(f"{ct}: {actual} != {expected[ct]}")
                        recommendations.append(f"Align {ct} to {expected[ct]}")
                if state.confidence < 0.5:
                    score *= state.confidence
                    dim_issues.append(f"Low confidence: {state.confidence:.2f}")
            dimensions.append(DimensionResult(dimension=ct, score=score, weight=weight, issues=dim_issues))

        overall = sum(d.weighted_score for d in dimensions) / max(0.001, sum(d.weight for d in dimensions))
        overall = max(0.0, min(1.0, overall))

        if overall >= 0.9:
            level = ValidationLevel.PASS
        elif overall >= 0.6:
            level = ValidationLevel.REVISE
        else:
            level = ValidationLevel.FAIL

        return ValidationResult(
            level=level,
            overall_score=overall,
            dimensions=dimensions,
            issues=issues,
            recommendations=recommendations,
        )

    def validate_snapshot(self, before: Dict[str, Any], after: Dict[str, Any]) -> ValidationResult:
        """Validate that two continuity snapshots are compatible."""
        dimensions: List[DimensionResult] = []
        issues: List[str] = []
        recommendations: List[str] = []
        for ct in CONTINUITY_TYPES:
            weight = self.weights.get(ct, 0.0)
            b = before.get(ct)
            a = after.get(ct)
            dim_issues: List[str] = []
            score = 1.0
            if b is None and a is None:
                score = 1.0
            elif b is None or a is None:
                score = 0.5
                dim_issues.append("One side missing")
            elif b != a:
                # Partial credit for numeric closeness.
                if isinstance(b, (int, float)) and isinstance(a, (int, float)):
                    diff = abs(b - a) / max(1e-6, max(abs(b), abs(a), 1.0))
                    score = max(0.0, 1.0 - diff)
                else:
                    score = 0.0
                dim_issues.append(f"Changed: {b} -> {a}")
                issues.append(f"{ct} changed")
                recommendations.append(f"Review {ct} change")
            dimensions.append(DimensionResult(dimension=ct, score=score, weight=weight, issues=dim_issues))
        overall = sum(d.weighted_score for d in dimensions) / max(0.001, sum(d.weight for d in dimensions))
        overall = max(0.0, min(1.0, overall))
        if overall >= 0.9:
            level = ValidationLevel.PASS
        elif overall >= 0.6:
            level = ValidationLevel.REVISE
        else:
            level = ValidationLevel.FAIL
        return ValidationResult(level=level, overall_score=overall, dimensions=dimensions, issues=issues, recommendations=recommendations)