"""
Competitive Gap Engine for MAKE AI Video Phase 22.

Compares MAKE capabilities against structured competitor capability catalogs.
Identifies missing, weak, strong, and unique capabilities.
Produces actionable engineering recommendations.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CapabilityStatus:
    MATCHED = "matched"
    EXCEEDED = "exceeded"
    PARTIALLY_MATCHED = "partially_matched"
    MISSING = "missing"
    NOT_COMPARABLE = "not_comparable"
    REQUIRES_EXTERNAL_PROVIDER = "requires_external_provider"


class CompetitorGapEngine:
    @staticmethod
    def analyze_gap(make_capability: Dict[str, Any], competitor_capability: Dict[str, Any]) -> Dict[str, Any]:
        make_status = make_capability.get("status", "not_configured")
        competitor_status = competitor_capability.get("status", "not_configured")

        if make_status == "not_configured" and competitor_status == "implemented":
            gap = "missing"
        elif make_status == "not_configured":
            gap = "not_comparable"
        elif competitor_status == "not_configured":
            gap = "not_comparable"
        elif make_status == "implemented" and competitor_status == "implemented":
            gap = "matched"
        elif make_status in ("implemented", "extended") and competitor_status == "implemented":
            gap = "matched"
        else:
            gap = "partially_matched"

        return {
            "capability": make_capability.get("name"),
            "make_status": make_status,
            "competitor_status": competitor_status,
            "gap": gap,
            "make_advantages": make_capability.get("advantages", []),
            "competitor_advantages": competitor_capability.get("advantages", []),
            "recommendation": CompetitorGapEngine._generate_recommendation(gap, make_capability),
        }

    @staticmethod
    def _generate_recommendation(gap: str, capability: Dict[str, Any]) -> str:
        if gap == "missing":
            return f"Implement {capability.get('name')} if high-impact and technically justified."
        elif gap == "partially_matched":
            return f"Strengthen {capability.get('name')} to match competitor depth."
        elif gap == "exceeded":
            return f"Maintain {capability.get('name')} leadership."
        elif gap == "matched":
            return f"Monitor {capability.get('name')} for competitive changes."
        return "No action required."

    @staticmethod
    def build_gap_report(make_capabilities: List[Dict[str, Any]], competitor_capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        gaps = []
        for make_cap in make_capabilities:
            for comp_cap in competitor_capabilities:
                if make_cap.get("name") == comp_cap.get("name"):
                    gaps.append(CompetitorGapEngine.analyze_gap(make_cap, comp_cap))

        summary = {
            "total_capabilities": len(make_capabilities),
            "matched": sum(1 for g in gaps if g["gap"] == "matched"),
            "exceeded": sum(1 for g in gaps if g["gap"] == "exceeded"),
            "partially_matched": sum(1 for g in gaps if g["gap"] == "partially_matched"),
            "missing": sum(1 for g in gaps if g["gap"] == "missing"),
            "not_comparable": sum(1 for g in gaps if g["gap"] == "not_comparable"),
        }
        return {"gaps": gaps, "summary": summary}


competitive_gap_engine = CompetitorGapEngine()
