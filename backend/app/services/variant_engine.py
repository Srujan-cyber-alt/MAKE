"""
Multi-Variant Generation Engine for MAKE AI Video.

Generates multiple creative versions from one project.

Example:
"Give me 5 versions."

Produces:
- different hooks
- camera variations
- pacing variations
- visual styles
- endings
- CTAs

Reuses assets and shared components.
"""

from typing import Optional, List, Dict, Any
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
import uuid
import logging

logger = logging.getLogger(__name__)


class VariantEngine:
    @staticmethod
    def generate_variants(
        creative_plan: Dict[str, Any],
        num_variants: int = 3,
        variation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        variation_types = variation_types or ["hook", "camera", "pacing", "style", "ending", "cta"]
        variants = []
        
        for i in range(num_variants):
            variant_plan = VariantEngine._create_variant(creative_plan, i, variation_types)
            storyboard = StoryboardEngine.generate_storyboard(variant_plan)
            script = ScriptEngine.generate_script(
                creative_plan=variant_plan,
                genre=creative_plan.get("genre", "commercial"),
                tone=creative_plan.get("tone", "cinematic"),
            )
            
            variants.append({
                "variant_id": f"variant:{uuid.uuid4()}",
                "variant_number": i + 1,
                "name": f"Version {i + 1}",
                "variations_applied": variation_types[:i + 1] if i < len(variation_types) else variation_types,
                "creative_plan": variant_plan,
                "storyboard": storyboard,
                "script": script,
            })
        
        return {
            "variants": variants,
            "total_variants": len(variants),
            "shared_components": ["characters", "products", "locations", "brand_dna"],
        }

    @staticmethod
    def _create_variant(base_plan: Dict[str, Any], variant_index: int, variation_types: List[str]) -> Dict[str, Any]:
        import copy
        variant = copy.deepcopy(base_plan)
        
        concept = variant.get("concept", {})
        concept["concept_id"] = str(uuid.uuid4())
        
        for vtype in variation_types[:variant_index + 1]:
            if vtype == "hook" and concept.get("cta"):
                concept["cta"] = VariantEngine._vary_cta()
            elif vtype == "camera":
                for shot in variant.get("shot_structure", []):
                    cam = shot.get("camera") or {}
                    cam["movement"] = VariantEngine._vary_camera_movement(cam.get("movement", "static"))
                    shot["camera"] = cam
            elif vtype == "pacing":
                for scene in variant.get("story_structure", []):
                    scene["duration_seconds"] = max(2.0, scene.get("duration_seconds", 5.0) * (0.8 + (variant_index * 0.1)))
            elif vtype == "style":
                concept["visual_language"] = VariantEngine._vary_visual_language(concept.get("visual_language", ""))
            elif vtype == "ending":
                concept["cta"] = VariantEngine._vary_cta()
        
        variant["concept"] = concept
        variant["variant_metadata"] = {
            "variant_index": variant_index,
            "variation_types": variation_types[:variant_index + 1],
        }
        return variant

    @staticmethod
    def _vary_cta() -> str:
        ctas = ["Shop Now", "Learn More", "Sign Up Today", "Download Free", "Get Started", "Join Now"]
        import random
        return random.choice(ctas)

    @staticmethod
    def _vary_camera_movement(current: str) -> str:
        alternatives = ["static", "push-in", "pull-out", "orbit", "pan", "tilt", "tracking", "handheld"]
        import random
        return random.choice([m for m in alternatives if m != current] or alternatives)

    @staticmethod
    def _vary_visual_language(current: str) -> str:
        alternatives = [
            "minimal, high-contrast, premium lighting",
            "anamorphic, deep shadows, dramatic lighting",
            "high saturation, dynamic angles, fast cuts",
            "soft, dreamy, pastel palette",
            "gritty, desaturated, documentary style",
        ]
        import random
        return random.choice(alternatives)
