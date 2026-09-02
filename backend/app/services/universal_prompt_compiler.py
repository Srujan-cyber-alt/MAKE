"""
Universal Prompt Compiler for MAKE AI Video Phase 16.

Compiles canonical creative representation into model-specific prompts.
"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class UniversalPromptCompiler:
    CANONICAL_FIELDS = [
        "subject", "action", "environment", "camera", "lens",
        "lighting", "style", "motion", "composition", "duration",
        "references", "negative_constraints",
    ]

    def __init__(self):
        self._compiler_versions = {}

    def compile(self, request, model_id: str, provider_id: str) -> Dict[str, Any]:
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        model = registry.get_model(model_id) if registry else None

        canonical = self._build_canonical(request)
        compiled = self._compile_for_model(canonical, model_id, provider_id, model)
        compiled["_compiler_version"] = "1.0"
        compiled["_model_id"] = model_id
        compiled["_provider_id"] = provider_id
        return compiled

    def _build_canonical(self, request) -> Dict[str, Any]:
        return {
            "subject": getattr(request, 'prompt', ''),
            "action": "",
            "environment": "",
            "camera": getattr(request, 'camera', {}),
            "lens": {},
            "lighting": {},
            "style": getattr(request, 'style', ''),
            "motion": getattr(request, 'motion', {}),
            "composition": {},
            "duration": getattr(request, 'duration_seconds', None),
            "references": getattr(request, 'references', []),
            "negative_constraints": getattr(request, 'negative_prompt', ''),
        }

    def _compile_for_model(self, canonical: Dict[str, Any], model_id: str, provider_id: str, model=None) -> Dict[str, Any]:
        compiled = {
            "prompt": self._build_prompt(canonical),
            "negative_prompt": canonical.get("negative_constraints", "") if (model and model.negative_prompt) else None,
            "duration_seconds": canonical.get("duration"),
            "aspect_ratio": self._infer_aspect_ratio(canonical),
            "seed": None,
            "parameters": {},
        }

        if canonical.get("camera") and model and model.camera_control:
            compiled["parameters"]["camera"] = canonical["camera"]

        if canonical.get("motion") and model and model.motion_control:
            compiled["parameters"]["motion"] = canonical["motion"]

        if canonical.get("references") and model and model.limits.max_reference_images > 0:
            compiled["parameters"]["reference_images"] = canonical["references"][:model.limits.max_reference_images]

        if model and model.supports_guidance_scale:
            compiled["parameters"]["guidance_scale"] = 7.5

        return compiled

    def _build_prompt(self, canonical: Dict[str, Any]) -> str:
        parts = []
        if canonical.get("subject"):
            parts.append(canonical["subject"])
        if canonical.get("action"):
            parts.append(canonical["action"])
        if canonical.get("environment"):
            parts.append(f"in {canonical['environment']}")
        if canonical.get("style"):
            parts.append(f"style: {canonical['style']}")
        if canonical.get("camera"):
            cam = canonical["camera"]
            if isinstance(cam, dict):
                parts.append(f"camera: {cam.get('movement', 'static')}")
        if canonical.get("motion"):
            motion = canonical["motion"]
            if isinstance(motion, dict):
                parts.append(f"motion: {motion.get('type', 'natural')}")
        return ", ".join(parts)

    def _infer_aspect_ratio(self, canonical: Dict[str, Any]) -> Optional[str]:
        composition = canonical.get("composition", {})
        if isinstance(composition, dict) and "aspect_ratio" in composition:
            return composition["aspect_ratio"]
        return None

    def translate_negative_prompt(self, negative_prompt: str, model_id: str) -> Optional[str]:
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        model = registry.get_model(model_id) if registry else None
        if model and model.negative_prompt:
            return negative_prompt
        return None


universal_prompt_compiler = UniversalPromptCompiler()
