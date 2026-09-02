"""
Cinematic Quality Score for MAKE AI Video Phase 18.

Production-level quality scoring across multiple dimensions.
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CinematicQualityScore:
    @staticmethod
    def score_production(production: Dict[str, Any]) -> Dict[str, Any]:
        dimensions = {}
        issues = []

        dimensions["technical"] = CinematicQualityScore._score_technical(production)
        dimensions["visual"] = CinematicQualityScore._score_visual(production)
        dimensions["continuity"] = CinematicQualityScore._score_continuity(production)
        dimensions["camera"] = CinematicQualityScore._score_camera(production)
        dimensions["motion"] = CinematicQualityScore._score_motion(production)
        dimensions["identity"] = CinematicQualityScore._score_identity(production)
        dimensions["product"] = CinematicQualityScore._score_product(production)
        dimensions["audio"] = CinematicQualityScore._score_audio(production)
        dimensions["editing"] = CinematicQualityScore._score_editing(production)
        dimensions["color"] = CinematicQualityScore._score_color(production)

        overall = sum(dimensions.values()) / len(dimensions) if dimensions else 0.0

        for dim, score in dimensions.items():
            if score < 0.5:
                issues.append(f"{dim} score below threshold: {score:.2f}")

        severity = "low"
        if overall < 0.3:
            severity = "critical"
        elif overall < 0.6:
            severity = "high"
        elif overall < 0.8:
            severity = "medium"

        return {
            "overall": overall,
            "dimensions": dimensions,
            "issues": issues,
            "severity": severity,
            "passed": overall >= 0.7,
            "blocking_issues": [i for i in issues if "critical" in severity or "high" in severity],
        }

    @staticmethod
    def _score_technical(production: Dict[str, Any]) -> float:
        score = 1.0
        if not production.get("master_output"):
            score -= 0.5
        if not production.get("qc_report"):
            score -= 0.3
        return max(0.0, score)

    @staticmethod
    def _score_visual(production: Dict[str, Any]) -> float:
        shots = production.get("shots", [])
        if not shots:
            return 0.0
        quality_scores = [s.get("quality_score", 0.5) for s in shots]
        return sum(quality_scores) / len(quality_scores)

    @staticmethod
    def _score_continuity(production: Dict[str, Any]) -> float:
        continuity = production.get("continuity_report") or {}
        return continuity.get("score", 0.5)

    @staticmethod
    def _score_camera(production: Dict[str, Any]) -> float:
        shots = production.get("shots", [])
        if not shots:
            return 0.0
        camera_plans = [s.get("camera") for s in shots if s.get("camera")]
        return 1.0 if len(camera_plans) == len(shots) else 0.7

    @staticmethod
    def _score_motion(production: Dict[str, Any]) -> float:
        shots = production.get("shots", [])
        if not shots:
            return 0.0
        motion_plans = [s.get("motion") for s in shots if s.get("motion")]
        return 1.0 if len(motion_plans) > 0 else 0.5

    @staticmethod
    def _score_identity(production: Dict[str, Any]) -> float:
        identity_issues = production.get("qc_report", {}).get("identity_issues", [])
        if identity_issues:
            return max(0.0, 1.0 - len(identity_issues) * 0.2)
        return 1.0

    @staticmethod
    def _score_product(production: Dict[str, Any]) -> float:
        product_issues = production.get("qc_report", {}).get("product_issues", [])
        if product_issues:
            return max(0.0, 1.0 - len(product_issues) * 0.2)
        return 1.0

    @staticmethod
    def _score_audio(production: Dict[str, Any]) -> float:
        audio_plan = production.get("audio_plan")
        if not audio_plan:
            return 0.5
        return 0.9 if audio_plan.get("mixed") else 0.6

    @staticmethod
    def _score_editing(production: Dict[str, Any]) -> float:
        edit_plan = production.get("edit_plan")
        if not edit_plan:
            return 0.5
        return 0.9 if edit_plan.get("assembled") else 0.6

    @staticmethod
    def _score_color(production: Dict[str, Any]) -> float:
        color_plan = production.get("color_plan")
        if not color_plan:
            return 0.5
        return 0.9 if color_plan.get("graded") else 0.6


cinematic_quality_score = CinematicQualityScore()
