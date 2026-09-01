import re
from typing import Optional, List, Dict, Any
from app.schemas.phase7 import SmartTargetSelection, TargetMatch, TargetCategory
from app.schemas.transformation import TargetSelectorType
from app.services.visual_analyzer import VisualAnalyzer
import logging

logger = logging.getLogger(__name__)


class SmartTargetSelector:
    LOCATION_KEYWORDS = {
        "left": ["left", "leftmost", "far left"],
        "right": ["right", "rightmost", "far right"],
        "center": ["center", "middle", "centre", "central"],
        "background": ["background", "behind", "rear", "back"],
        "foreground": ["foreground", "front", "closest"],
    }

    @staticmethod
    async def select_target(
        prompt: str,
        detected_targets: List[Dict[str, Any]],
        asset_id: str,
        project_id: str,
        user_id: str,
    ) -> SmartTargetSelection:
        prompt_lower = prompt.lower()
        location = SmartTargetSelector._extract_location(prompt_lower)
        target_type, target_label = SmartTargetSelector._extract_type_and_label(prompt_lower)

        matches = []
        for target in detected_targets:
            category = target.get("category", "object")
            label = target.get("label", "")
            confidence = target.get("confidence", 0.0)
            bbox = target.get("bbox")

            type_match = SmartTargetSelector._category_matches(target_type, category)
            loc_match = SmartTargetSelector._location_matches(location, bbox)
            if type_match and (loc_match or not location):
                matches.append(TargetMatch(
                    target_id=target.get("target_id", ""),
                    category=TargetCategory(category),
                    label=label,
                    confidence=confidence,
                    is_ambiguous=False,
                ))

        if not matches and detected_targets:
            best = max(detected_targets, key=lambda t: t.get("confidence", 0))
            matches.append(TargetMatch(
                target_id=best.get("target_id", ""),
                category=TargetCategory(best.get("category", "object")),
                label=best.get("label", ""),
                confidence=best.get("confidence", 0.0) * 0.5,
                is_ambiguous=True,
            ))

        if len(matches) > 1:
            for m in matches:
                m.is_ambiguous = True
            primary = max(matches, key=lambda m: m.confidence)
            return SmartTargetSelection(
                matches=matches,
                primary_target=primary,
                requires_clarification=True,
                clarification_options=[{"target_id": m.target_id, "label": m.label} for m in matches],
            )

        primary = matches[0] if matches else None
        return SmartTargetSelection(
            matches=matches,
            primary_target=primary,
            requires_clarification=primary is None,
            clarification_options=[{"target_id": m.target_id, "label": m.label} for m in matches] if matches else [],
        )

    @staticmethod
    def _extract_location(prompt: str) -> Optional[str]:
        for loc, keywords in SmartTargetSelector.LOCATION_KEYWORDS.items():
            for kw in keywords:
                if kw in prompt:
                    return loc
        return None

    @staticmethod
    def _extract_type_and_label(prompt: str) -> tuple[Optional[str], Optional[str]]:
        type_keywords = {
            "person": ["person", "man", "woman", "guy", "girl", "people"],
            "object": ["object", "thing", "car", "phone", "bottle", "product"],
            "background": ["background", "scene", "setting"],
            "face": ["face", "head"],
            "product": ["product", "item", "package"],
            "clothing": ["clothes", "clothing", "shirt", "dress", "jacket"],
        }
        for t_type, keywords in type_keywords.items():
            for kw in keywords:
                if kw in prompt:
                    return t_type, kw
        return None, None

    @staticmethod
    def _category_matches(target_type: Optional[str], category: str) -> bool:
        if not target_type:
            return True
        mapping = {
            "person": ["person"],
            "object": ["object", "product", "vehicle", "animal"],
            "background": ["background", "sky"],
            "face": ["face"],
            "product": ["product"],
            "clothing": ["clothing"],
        }
        allowed = mapping.get(target_type, [])
        return category in allowed or target_type == category

    @staticmethod
    def _location_matches(location: Optional[str], bbox: Optional[Dict[str, Any]]) -> bool:
        if not location or not bbox:
            return True
        x = bbox.get("x", 0)
        width = bbox.get("width", 0)
        center = x + width / 2
        if location == "left":
            return center < 0.33
        elif location == "right":
            return center > 0.66
        elif location == "center":
            return 0.33 <= center <= 0.66
        elif location == "background":
            return bbox.get("depth", 0) > 0.5
        elif location == "foreground":
            return bbox.get("depth", 0) <= 0.5
        return True
