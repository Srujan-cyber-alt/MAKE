"""Creative Director — produces structured creative decisions for visual requests.

Plans, does not fabricate generation results. Output is a structured
CreativeDecision that downstream engines can use.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.intelligence.schemas import CreativeDecision, Intent


class CreativeDirector:
    """Generates creative direction plans based on prompts and constraints."""

    COMPOSITION_PRESETS: Dict[str, Dict[str, Any]] = {
        "cinematic": {
            "rule_of_thirds": True,
            "leading_lines": True,
            "depth_of_field": "shallow",
            "framing": "wide",
        },
        "portrait": {
            "rule_of_thirds": True,
            "face_position": "left_third",
            "depth_of_field": "medium",
        },
        "macro": {
            "focus_point": "subject_center",
            "depth_of_field": "very_shallow",
            "framing": "tight",
        },
    }

    CAMERA_PRESETS: Dict[str, Dict[str, Any]] = {
        "orbit": {"movement": "orbit", "angle": "eye_level", "speed": "slow"},
        "dolly": {"movement": "dolly_in", "angle": "low", "speed": "medium"},
        "handheld": {"movement": "handheld", "angle": "variable", "speed": "fast"},
        "static": {"movement": "static", "angle": "eye_level"},
    }

    LIGHTING_PRESETS: Dict[str, Dict[str, Any]] = {
        "golden_hour": {
            "type": "natural", "direction": "back_left",
            "temperature": "warm", "contrast": "soft",
        },
        "noir": {
            "type": "dramatic", "direction": "side",
            "temperature": "cool", "contrast": "high",
        },
        "studio": {
            "type": "artificial", "direction": "front",
            "temperature": "neutral", "contrast": "controlled",
        },
    }

    MOODS: Dict[str, Dict[str, Any]] = {
        "dramatic": {"color_palette": "high_contrast", "energy": "high"},
        "serene": {"color_palette": "muted", "energy": "low"},
        "tense": {"color_palette": "desaturated_reds", "energy": "high"},
        "nostalgic": {"color_palette": "warm_desaturated", "energy": "medium"},
        "epic": {"color_palette": "wide_gamut", "energy": "high"},
    }

    def __init__(self) -> None:
        pass

    def plan(
        self,
        prompt: str,
        intent: Optional[Intent] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> CreativeDecision:
        """Produce a structured creative decision from a prompt (CPU-native)."""
        lowered = prompt.lower()
        analysis = self._analyse(lowered, intent, constraints or {})
        return CreativeDecision(
            composition=analysis["composition"],
            camera=analysis["camera"],
            lighting=analysis["lighting"],
            materials=analysis["materials"],
            environment=analysis["environment"],
            subject=analysis["subject"],
            mood=analysis["mood_label"],
            realism=analysis["realism"],
            cinematic_intent=analysis["cinematic_intent"],
            rationale=analysis["rationale"],
            notes=analysis["notes"],
        )

    # ------------------------------------------------------------------

    def _analyse(
        self,
        lowered: str,
        intent: Optional[Intent],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        composition = self._match_keyword(lowered, self.COMPOSITION_PRESETS, "cinematic")
        camera = self._match_keyword(lowered, self.CAMERA_PRESETS, "static")
        lighting = self._match_keyword(lowered, self.LIGHTING_PRESETS, "golden_hour")
        mood_label = self._match_keyword(lowered, self.MOODS, "dramatic")["preset"]

        realism = "photorealistic"
        if "stylized" in lowered or "anime" in lowered:
            realism = "stylized"
        elif "cartoon" in lowered or "illustration" in lowered:
            realism = "illustrative"

        materials: Dict[str, Any] = {"surfaces": [], "textures": []}
        environment: Dict[str, Any] = {"type": "interior", "details": []}

        if "outdoor" in lowered or "outside" in lowered or "city" in lowered or "nature" in lowered:
            environment["type"] = "exterior"
        if "rain" in lowered:
            environment["details"].append("rain")
            materials["textures"].append("wet")
        if "fire" in lowered or "flames" in lowered:
            materials["textures"].append("fiery")
        if "metal" in lowered or "steel" in lowered:
            materials["surfaces"].append("metallic")
        if "wood" in lowered:
            materials["surfaces"].append("wood")

        subject: Dict[str, Any] = {"type": "person", "details": []}
        if "car" in lowered or "vehicle" in lowered:
            subject["type"] = "vehicle"
        elif "animal" in lowered:
            subject["type"] = "animal"

        cinematic_intent = "cinematic"
        if "documentary" in lowered:
            cinematic_intent = "documentary"
        elif "commercial" in lowered:
            cinematic_intent = "commercial"

        notes: List[str] = []
        if intent:
            for entity in intent.entities:
                if entity.type.value == "person":
                    notes.append(f"Recognised person entity: {entity.name}")

        return {
            "composition": composition,
            "camera": camera,
            "lighting": lighting,
            "materials": materials,
            "environment": environment,
            "subject": subject,
            "mood_label": mood_label,
            "realism": realism,
            "cinematic_intent": cinematic_intent,
            "rationale": f"Creative plan derived from prompt analysis with realism={realism}",
            "notes": notes,
        }

    @staticmethod
    def _match_keyword(
        lowered: str, presets: Dict[str, Dict[str, Any]], default_key: str
    ) -> Dict[str, Any]:
        for key, preset in presets.items():
            if key in lowered:
                result = dict(preset)
                result["preset"] = key
                return result
        result = dict(presets[default_key])
        result["preset"] = default_key
        return result
