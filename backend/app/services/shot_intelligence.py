"""
Shot Intelligence for MAKE AI Video Phase 19.

Estimates shot importance, difficulty, and risk.
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ShotPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HERO = "hero"


class ShotDifficulty:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ShotIntelligence:
    @staticmethod
    def evaluate(shot: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        priority = ShotIntelligence._evaluate_priority(shot, context)
        difficulty = ShotIntelligence._evaluate_difficulty(shot, context)
        risk = ShotIntelligence._calculate_risk(shot, context, difficulty)
        variant_count = ShotIntelligence._suggest_variant_count(priority, difficulty, risk)
        return {
            "shot_id": shot.get("shot_id"),
            "priority": priority,
            "difficulty": difficulty,
            "risk_score": risk,
            "suggested_variant_count": variant_count,
            "suggested_repair_attempts": 3 if difficulty in ("high", "extreme") else 2,
        }

    @staticmethod
    def _evaluate_priority(shot: Dict[str, Any], context: Dict[str, Any]) -> str:
        description = (shot.get("description") or "").lower()
        shot_type = (shot.get("shot_type") or "").lower()
        if "hero" in description or "macro" in shot_type or "close_up" in shot_type:
            return ShotPriority.HERO
        if shot.get("product_id") or "product" in description:
            return ShotPriority.HIGH
        if "character" in description or shot.get("character_id"):
            return ShotPriority.MEDIUM
        return ShotPriority.LOW

    @staticmethod
    def _evaluate_difficulty(shot: Dict[str, Any], context: Dict[str, Any]) -> str:
        score = 0
        if shot.get("character_id"):
            score += 1
        if shot.get("motion"):
            score += 1
        if shot.get("camera", {}).get("movement") and shot["camera"]["movement"] != "static":
            score += 1
        if shot.get("duration_seconds", 5) > 10:
            score += 1
        if context.get("world") and context["world"].get("weather") in ("rain", "snow", "fog"):
            score += 1
        if score >= 4:
            return ShotDifficulty.EXTREME
        if score >= 3:
            return ShotDifficulty.HIGH
        if score >= 2:
            return ShotDifficulty.MEDIUM
        return ShotDifficulty.LOW

    @staticmethod
    def _calculate_risk(shot: Dict[str, Any], context: Dict[str, Any], difficulty: str) -> float:
        base = 0.2
        if difficulty == ShotDifficulty.EXTREME:
            base += 0.4
        elif difficulty == ShotDifficulty.HIGH:
            base += 0.25
        elif difficulty == ShotDifficulty.MEDIUM:
            base += 0.1
        references = len(shot.get("references", [])) + len(context.get("reference_asset_ids", []))
        base -= min(0.2, references * 0.05)
        return max(0.0, min(1.0, base))

    @staticmethod
    def _suggest_variant_count(priority: str, difficulty: str, risk: float) -> int:
        if priority == ShotPriority.HERO:
            return 3
        if difficulty in (ShotDifficulty.HIGH, ShotDifficulty.EXTREME):
            return 2
        if risk > 0.6:
            return 2
        return 1


shot_intelligence = ShotIntelligence()
