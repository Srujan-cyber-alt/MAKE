from typing import Optional, List, Dict, Any
from app.schemas.phase9 import CinematicPromptCompilation
import re
import logging

logger = logging.getLogger(__name__)


class AdvancedPromptCompiler:
    COMPONENT_KEYWORDS = {
        "subject": ["a person", "a man", "a woman", "a child", "a model", "the person", "the subject", "a character"],
        "action": ["walking", "running", "jumping", "dancing", "talking", "sitting", "standing", "gesturing", "throwing", "catching", "picking up", "opening", "closing", "driving", "riding", "looking", "smiling", "crying", "turning", "fighting"],
        "environment": ["city", "beach", "forest", "office", "studio", "street", "park", "mountain", "space", "underwater", "room", "car", "kitchen", "rooftop", "desert", "snow"],
        "time_of_day": ["morning", "day", "afternoon", "evening", "sunset", "dusk", "night", "midnight", "golden hour", "blue hour"],
        "weather": ["sunny", "cloudy", "rainy", "snowy", "foggy", "stormy", "windy", "clear", "overcast", "misty"],
        "wardrobe": ["suit", "dress", "casual", "formal", "uniform", "jacket", "hoodie", "black clothes", "red dress", "white shirt"],
        "shot_type": ["wide shot", "medium shot", "close-up", "extreme close-up", "over the shoulder", "bird's eye", "low angle", "dutch angle", "POV"],
        "camera_movement": ["orbit", "dolly", "push in", "pull out", "pan", "tilt", "zoom", "handheld", "crane", "drone", "whip pan", "racking focus"],
        "lighting": ["cinematic lighting", "dramatic lighting", "soft lighting", "hard lighting", "rim light", "backlight", "key light", "fill light", "golden hour light", "neon light", "moody lighting"],
        "style": ["cinematic", "commercial", "film", "documentary", "vintage", "neon", "dark", "bright", "warm", "cool", "premium", "luxury", "sports", "noir"],
        "motion": ["slow motion", "fast motion", "time lapse", "real time", "fluid", "energetic", "smooth", "dynamic"],
    }

    @staticmethod
    def compile_from_prompt(prompt: str, context: Optional[Dict[str, Any]] = None) -> CinematicPromptCompilation:
        context = context or {}
        prompt_lower = prompt.lower()
        compilation = CinematicPromptCompilation()

        for component, keywords in AdvancedPromptCompiler.COMPONENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    setattr(compilation, component, keyword)
                    break

        if "futuristic" in prompt_lower or "cyberpunk" in prompt_lower:
            compilation.style = "futuristic"
            compilation.atmosphere = "futuristic"
        if "luxury" in prompt_lower or "premium" in prompt_lower:
            compilation.style = "luxury"
        if "action" in prompt_lower or "explosion" in prompt_lower:
            compilation.style = "action"
            compilation.pacing = "fast"
        if "rain" in prompt_lower:
            compilation.weather = "rainy"
            compilation.atmosphere = "rainy"
        if "night" in prompt_lower:
            compilation.time_of_day = "night"
        if "stormy" in prompt_lower:
            compilation.weather = "stormy"
            compilation.atmosphere = "stormy"

        if "person's identity" in prompt_lower or "keep identity" in prompt_lower or "preserve identity" in prompt_lower:
            compilation.continuity.append("preserve_identity")
        if "product" in prompt_lower and "consistent" in prompt_lower:
            compilation.continuity.append("preserve_product")
        if "background" in prompt_lower and "keep" in prompt_lower:
            compilation.continuity.append("preserve_background")

        negative_keywords = ["blurry", "low quality", "distorted", "ugly", "deformed", "bad anatomy", "watermark", "text", "logo", "amateur"]
        compilation.negative_constraints = [kw for kw in negative_keywords if kw in prompt_lower]
        if not compilation.negative_constraints:
            compilation.negative_constraints = ["blurry", "low quality", "distorted"]

        compilation.compiled_prompt = AdvancedPromptCompiler._build_compiled_prompt(compilation)
        return compilation

    @staticmethod
    def _build_compiled_prompt(compilation: CinematicPromptCompilation) -> str:
        parts = []
        if compilation.subject:
            parts.append(f"SUBJECT: {compilation.subject}")
        if compilation.action:
            parts.append(f"ACTION: {compilation.action}")
        if compilation.environment:
            parts.append(f"ENVIRONMENT: {compilation.environment}")
        if compilation.time_of_day:
            parts.append(f"TIME: {compilation.time_of_day}")
        if compilation.weather:
            parts.append(f"WEATHER: {compilation.weather}")
        if compilation.wardrobe:
            parts.append(f"WARDROBE: {compilation.wardrobe}")
        if compilation.shot_type:
            parts.append(f"SHOT: {compilation.shot_type}")
        if compilation.camera_movement:
            parts.append(f"CAMERA: {compilation.camera_movement}")
        if compilation.lighting:
            parts.append(f"LIGHTING: {compilation.lighting}")
        if compilation.style:
            parts.append(f"STYLE: {compilation.style}")
        if compilation.motion:
            parts.append(f"MOTION: {compilation.motion}")
        if compilation.atmosphere:
            parts.append(f"ATMOSPHERE: {compilation.atmosphere}")
        if compilation.continuity:
            parts.append(f"CONTINUITY: {', '.join(compilation.continuity)}")
        if compilation.negative_constraints:
            parts.append(f"NEGATIVE: {', '.join(compilation.negative_constraints)}")
        return "\n".join(parts)

    @staticmethod
    def compile_for_provider(compilation: CinematicPromptCompilation, provider: str) -> str:
        base = compilation.compiled_prompt or ""
        provider_prefixes = {
            "runway": "Cinematic, high-quality video. ",
            "pika": "High quality, detailed video. ",
            "test": "Test video. ",
        }
        prefix = provider_prefixes.get(provider, "")
        return f"{prefix}{base}" if prefix else base
