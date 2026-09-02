"""
Production Templates for MAKE AI Video Phase 18.

Reusable production configurations.
"""

from typing import Optional, Dict, Any, List
from app.services.creative_director import Genre, Tone


class ProductionTemplate:
    @staticmethod
    def get_template(template_id: str) -> Optional[Dict[str, Any]]:
        templates = {
            "product_ad": {
                "template_id": "product_ad",
                "name": "Product Advertisement",
                "goal": "commercial",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "structure": ["hook", "product_reveal", "demonstration", "lifestyle", "cta"],
                "shot_types": ["wide", "medium", "close_up", "macro", "detail"],
                "camera_style": "smooth_push_in",
                "lighting_style": "product",
                "color_style": "commercial",
                "audio_style": "upbeat_music",
            },
            "cinematic_film": {
                "template_id": "cinematic_film",
                "name": "Cinematic Film",
                "goal": "short_film",
                "duration_seconds": 60,
                "aspect_ratio": "21:9",
                "structure": ["opening", "inciting_event", "rising_action", "climax", "resolution"],
                "shot_types": ["wide", "medium", "close_up", "over_shoulder", "dutch"],
                "camera_style": "cinematic",
                "lighting_style": "low_key",
                "color_style": "cinematic",
                "audio_style": "orchestral",
            },
            "social_reel": {
                "template_id": "social_reel",
                "name": "Social Reel",
                "goal": "social_video",
                "duration_seconds": 15,
                "aspect_ratio": "9:16",
                "structure": ["hook", "escalation", "payoff", "cta"],
                "shot_types": ["close_up", "medium", "detail"],
                "camera_style": "dynamic",
                "lighting_style": "high_key",
                "color_style": "bold",
                "audio_style": "trending",
            },
            "fashion_film": {
                "template_id": "fashion_film",
                "name": "Fashion Film",
                "goal": "fashion_film",
                "duration_seconds": 45,
                "aspect_ratio": "9:16",
                "structure": ["opening", "runway", "detail", "movement", "finale"],
                "shot_types": ["wide", "medium", "close_up", "low_angle"],
                "camera_style": "smooth_tracking",
                "lighting_style": "studio",
                "color_style": "film",
                "audio_style": "electronic",
            },
            "sports_ad": {
                "template_id": "sports_ad",
                "name": "Sports Advertisement",
                "goal": "commercial",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "structure": ["hook", "action", "product", "cta"],
                "shot_types": ["wide", "medium", "close_up", "low_angle", "dutch"],
                "camera_style": "handheld",
                "lighting_style": "dramatic",
                "color_style": "bold",
                "audio_style": "energetic",
            },
        }
        return templates.get(template_id)

    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        return [
            ProductionTemplate.get_template("product_ad"),
            ProductionTemplate.get_template("cinematic_film"),
            ProductionTemplate.get_template("social_reel"),
            ProductionTemplate.get_template("fashion_film"),
            ProductionTemplate.get_template("sports_ad"),
        ]

    @staticmethod
    def apply_template(template_id: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        template = ProductionTemplate.get_template(template_id)
        if not template:
            return {"error": f"Template {template_id} not found"}
        if overrides:
            template = {**template, **overrides}
        return template


production_templates = ProductionTemplate()
