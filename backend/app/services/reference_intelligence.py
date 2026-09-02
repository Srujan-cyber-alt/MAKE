"""
Reference Intelligence for MAKE AI Video Phase 19.

Extends ReferenceManager with classification, sufficiency, and conflict detection.
"""

from typing import Optional, List, Dict, Any
from app.services.reference_manager import reference_manager
import logging

logger = logging.getLogger(__name__)


class ReferenceCategory:
    CHARACTER = "character"
    PRODUCT = "product"
    LOCATION = "location"
    STYLE = "style"
    WARDROBE = "wardrobe"
    PROP = "prop"
    COMPOSITION = "composition"
    FIRST_FRAME = "first_frame"
    LAST_FRAME = "last_frame"


class ReferenceIntelligence:
    @staticmethod
    def classify(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        classified = []
        for ref in references:
            category = ReferenceIntelligence._detect_category(ref)
            classified.append({
                "reference": ref,
                "category": category,
                "sufficient": True,
            })
        return classified

    @staticmethod
    def _detect_category(ref: Dict[str, Any]) -> str:
        ref_type = (ref.get("type") or "").lower()
        if "character" in ref_type or "face" in ref_type:
            return ReferenceCategory.CHARACTER
        if "product" in ref_type:
            return ReferenceCategory.PRODUCT
        if "location" in ref_type or "environment" in ref_type:
            return ReferenceCategory.LOCATION
        if "style" in ref_type:
            return ReferenceCategory.STYLE
        if "wardrobe" in ref_type or "clothing" in ref_type:
            return ReferenceCategory.WARDROBE
        if "first" in ref_type:
            return ReferenceCategory.FIRST_FRAME
        if "last" in ref_type:
            return ReferenceCategory.LAST_FRAME
        return ReferenceCategory.PROP

    @staticmethod
    def detect_conflicts(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        conflicts = []
        by_category = {}
        for ref in references:
            category = ReferenceIntelligence._detect_category(ref)
            by_category.setdefault(category, []).append(ref)

        for category, refs in by_category.items():
            if len(refs) > 1:
                labels = [r.get("label", r.get("url", "")) for r in refs]
                if len(set(labels)) > 1:
                    conflicts.append({
                        "type": "REFERENCE_CONFLICT",
                        "category": category,
                        "references": labels,
                        "recommendation": "Resolve conflict before generation",
                    })
        return conflicts

    @staticmethod
    def select_for_shot(shot: Dict[str, Any], references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not references:
            return []
        shot_type = (shot.get("shot_type") or "").lower()
        selected = []
        for ref in references:
            category = ReferenceIntelligence._detect_category(ref)
            if "close_up" in shot_type and category in (ReferenceCategory.CHARACTER, ReferenceCategory.PRODUCT):
                selected.append(ref)
            elif "wide" in shot_type and category == ReferenceCategory.LOCATION:
                selected.append(ref)
            else:
                selected.append(ref)
        return selected


reference_intelligence = ReferenceIntelligence()
