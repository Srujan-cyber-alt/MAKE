"""
Continuity Engine for MAKE AI Video Phase 18.

Cross-shot continuity validation for:
- identity
- wardrobe
- product
- world
- lighting
- camera
- motion
- composition
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ContinuityEngine:
    CONTINUITY_DIMENSIONS = [
        "identity",
        "wardrobe",
        "product",
        "world",
        "lighting",
        "camera",
        "motion",
        "composition",
    ]

    @staticmethod
    def validate_shot_continuity(shots: List[Dict[str, Any]], constraints: Dict[str, Any]) -> Dict[str, Any]:
        if not shots:
            return {"consistent": True, "score": 1.0, "issues": []}

        issues = []
        scores = {}

        for dimension in ContinuityEngine.CONTINUITY_DIMENSIONS:
            score, dim_issues = ContinuityEngine._validate_dimension(shots, dimension, constraints)
            scores[dimension] = score
            issues.extend(dim_issues)

        overall = sum(scores.values()) / len(scores) if scores else 1.0
        return {
            "consistent": len(issues) == 0,
            "score": overall,
            "dimensions": scores,
            "issues": issues,
            "total_shots_analyzed": len(shots),
        }

    @staticmethod
    def _validate_dimension(shots: List[Dict[str, Any]], dimension: str, constraints: Dict[str, Any]) -> tuple:
        issues = []
        score = 1.0

        if dimension == "identity":
            characters = [s.get("character_id") for s in shots if s.get("character_id")]
            if len(set(characters)) > 1:
                issues.append("Multiple different characters detected across shots")
                score -= 0.3

        elif dimension == "wardrobe":
            wardrobes = [s.get("wardrobe") for s in shots if s.get("wardrobe")]
            if len(set(str(w) for w in wardrobes)) > 1:
                issues.append("Wardrobe inconsistency detected")
                score -= 0.2

        elif dimension == "product":
            products = [s.get("product_id") for s in shots if s.get("product_id")]
            if len(set(products)) > 1:
                issues.append("Multiple products in sequence")
                score -= 0.2

        elif dimension == "world":
            worlds = [s.get("world_id") for s in shots if s.get("world_id")]
            if len(set(worlds)) > 1:
                issues.append("Multiple worlds detected")
                score -= 0.3

        elif dimension == "lighting":
            lightings = [s.get("lighting") for s in shots if s.get("lighting")]
            if len(set(lightings)) > 1:
                issues.append("Lighting direction mismatch across shots")
                score -= 0.2

        elif dimension == "camera":
            movements = [s.get("camera", {}).get("movement") for s in shots if s.get("camera")]
            if len(set(movements)) > 3:
                issues.append("Inconsistent camera movement")
                score -= 0.1

        elif dimension == "motion":
            motions = [s.get("motion", {}).get("action") for s in shots if s.get("motion")]
            if len(set(motions)) > len(shots) * 2:
                issues.append("Motion inconsistency detected")
                score -= 0.1

        elif dimension == "composition":
            compositions = [s.get("composition") for s in shots if s.get("composition")]
            if len(set(str(c) for c in compositions)) > len(shots):
                issues.append("Composition inconsistency")
                score -= 0.1

        return max(0.0, score), issues

    @staticmethod
    def check_world_consistency(world: Dict[str, Any], scene: Dict[str, Any]) -> Dict[str, Any]:
        if not world:
            return {"consistent": True, "issues": []}

        issues = []
        if world.get("lighting") and scene.get("lighting"):
            if world["lighting"] != scene["lighting"]:
                issues.append(f"Lighting mismatch: world={world['lighting']}, scene={scene['lighting']}")
        if world.get("time") and scene.get("time"):
            if world["time"] != scene["time"]:
                issues.append(f"Time mismatch: world={world['time']}, scene={scene['time']}")
        if world.get("weather") and scene.get("weather"):
            if world["weather"] != scene["weather"]:
                issues.append(f"Weather mismatch: world={world['weather']}, scene={scene['weather']}")

        return {"consistent": len(issues) == 0, "issues": issues}


continuity_engine = ContinuityEngine()
