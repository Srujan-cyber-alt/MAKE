import re
from typing import List, Dict, Any, Optional
from app.schemas.transformation import (
    TransformationOperation,
    TargetSelector,
    TargetSelectorType,
    TransformationType,
    VFXLayer,
    VFXLayerType,
    BlendMode,
)


class TransformationAnalyzer:
    TRANSFORMATION_KEYWORDS = {
        TransformationType.OBJECT_REMOVAL: [
            r"\bremove\b.*?\b(person|man|woman|object|thing|car|phone|bottle|sign)\b",
            r"\b(delete|erase|get rid of|eliminate)\b.*?\b(person|man|woman|object|thing)\b",
            r"\b(remove|delete|erase)\b.*?\b(from|in|from the)\b",
        ],
        TransformationType.OBJECT_REPLACEMENT: [
            r"\breplace\b.*?\b(phone|car|bottle|object|thing|clothes|clothing)\b",
            r"\bchange\b.*?\b(phone|car|bottle|object|clothes)\b.*?\bto\b",
            r"\bswap\b.*?\b(phone|car|bottle|object)\b",
        ],
        TransformationType.BACKGROUND_REPLACEMENT: [
            r"\breplace\b.*?\b(background|scene|setting|location|street|sky)\b",
            r"\bput\b.*?\b(in|inside|into)\b.*?\b(luxury|futuristic|studio|hotel|beach|forest|city)\b",
            r"\bchange\b.*?\bbackground\b",
            r"\bbackground\b.*?\bto\b",
        ],
        TransformationType.STYLE_TRANSFER: [
            r"\bmake\b.*?\blook\b.*?\b(like|as)\b",
            r"\bstyle\b.*?\bof\b",
            r"\bturn\b.*?\binto\b.*?\b(hollywood|cinematic|anime|realistic|painting)\b",
            r"\bcinematic\b",
        ],
        TransformationType.MOTION_TRANSFER: [
            r"\bmake\b.*?\b(perform|dance|move|walk|run|jump|fight|action)\b",
            r"\bmotion\s*transfer\b",
            r"\breference\s*motion\b",
            r"\b(action|performance|gesture|dance)\b.*?\breference\b",
        ],
        TransformationType.CAMERA_TRANSFORM: [
            r"\b(zoom|dolly|orbit|pan|tilt|tracking|crane|handheld|drone)\b",
            r"\bcamera\b.*?\b(orbit|move|rotate|pan|tilt|zoom|dolly)\b",
            r"\bmake\b.*?\bcamera\b",
        ],
        TransformationType.VFX_APPLY: [
            r"\b(add|apply|create)\b.*?\b(fire|smoke|rain|snow|fog|sparks|lightning|explosion|energy|glow|dust|particles|weather)\b",
            r"\b(fire|smoke|rain|snow|fog|sparks|lightning|explosion)\b.*?\b(from|on|in)\b",
        ],
        TransformationType.INPAINTING: [
            r"\bfill\b.*?\b(background|area|hole|missing|gap)\b",
            r"\binpaint\b",
            r"\bextend\b.*?\b(object|edge|boundary)\b",
        ],
        TransformationType.OUTPAINTING: [
            r"\bextend\b.*?\b(frame|video|border|edge)\b",
            r"\boutpaint\b",
            r"\bexpand\b.*?\b(frame|canvas|view)\b",
        ],
        TransformationType.ENVIRONMENT_TRANSFORM: [
            r"\b(day|night|sunny|cloudy|rainy|snowy|summer|winter)\b.*?\bto\b.*?\b(day|night|sunny|cloudy|rainy|snowy|summer|winter)\b",
            r"\bchange\b.*?\b(weather|environment|lighting|time of day)\b",
            r"\bturn\b.*?\b(day|night|sunny)\b",
        ],
        TransformationType.ACTION_TRANSFORM: [
            r"\bmake\b.*?\b(sit|stand|walk|run|jump|turn|pick up|throw|catch|fight|dance|fly)\b",
            r"\bchange\b.*?\b(action|movement|behavior|pose)\b",
            r"\bmake\b.*?\bperson\b.*?\b(action)\b",
        ],
        TransformationType.LIGHTING_TRANSFORM: [
            r"\bchange\b.*?\b(lighting|light|exposure|brightness)\b",
            r"\bmake\b.*?\b(brighter|darker|warmer|colder|softer|harsher)\b",
            r"\b(studio|cinematic|dramatic|natural)\b.*?\blighting\b",
        ],
        TransformationType.WEATHER_TRANSFORM: [
            r"\b(add|make|change to)\b.*?\b(rain|snow|fog|storm|wind|sunny|cloudy)\b",
            r"\bweather\b.*?\b(rain|snow|fog|storm)\b",
            r"\braining\b|\bsnowing\b|\bfoggy\b",
        ],
        TransformationType.IDENTITY_PRESERVE: [
            r"\bkeep\b.*?\b(face|identity|character|person|clothes|hair|look)\b.*?\b(same|exact|identical)\b",
            r"\bpreserve\b.*?\b(identity|face|character)\b",
            r"\bconsistent\b.*?\bcharacter\b",
        ],
        TransformationType.VIDEO_TO_VIDEO: [
            r"\bvideo\s*to\s*video\b",
            r"\btransform\b.*?\bvideo\b",
            r"\breframe\b.*?\bvideo\b",
        ],
    }

    TARGET_PATTERNS = {
        TargetSelectorType.PERSON: [
            r"\b(person|man|woman|guy|girl|boy|kid|child|people|character|actor|model)\b",
        ],
        TargetSelectorType.OBJECT: [
            r"\b(car|phone|bottle|chair|table|door|sign|ball|box|laptop|watch|product|dress|hat|glasses|bag)\b",
        ],
        TargetSelectorType.BACKGROUND: [
            r"\b(background|scene|setting|location|street|sky|wall|floor|room|environment)\b",
        ],
        TargetSelectorType.FACE: [
            r"\b(face|head|facial|expression)\b",
        ],
        TargetSelectorType.PRODUCT: [
            r"\b(product|item|package|box|label|logo|brand)\b",
        ],
        TargetSelectorType.LIGHTING: [
            r"\b(lighting|light|exposure|brightness|contrast|shadow|highlight)\b",
        ],
        TargetSelectorType.CAMERA: [
            r"\b(camera|shot|angle|perspective|view|frame|zoom|dolly|orbit|pan|tilt)\b",
        ],
        TargetSelectorType.ENVIRONMENT: [
            r"\b(weather|rain|snow|fog|storm|sunny|cloudy|day|night|season|temperature)\b",
        ],
    }

    VFX_PATTERNS = {
        VFXLayerType.FIRE: [r"\bfire\b", r"\bflame\b", r"\bburning\b", r"\bflames\b"],
        VFXLayerType.SMOKE: [r"\bsmoke\b", r"\bsmoky\b", r"\bfog\b"],
        VFXLayerType.RAIN: [r"\brain\b", r"\braining\b", r"\bwater\s*drops\b"],
        VFXLayerType.SNOW: [r"\bsnow\b", r"\bsnowing\b", r"\bsnowflakes\b"],
        VFXLayerType.FOG: [r"\bfog\b", r"\bmist\b", r"\bhaze\b"],
        VFXLayerType.SPARKS: [r"\bsparks\b", r"\bsparkle\b", r"\bsparkling\b"],
        VFXLayerType.LIGHTNING: [r"\blightning\b", r"\bthunder\b", r"\belectrical\b"],
        VFXLayerType.GLOW: [r"\bglow\b", r"\bluminous\b", r"\bglowing\b"],
        VFXLayerType.EXPLOSION: [r"\bexplosion\b", r"\bexplode\b", r"\bblast\b"],
        VFXLayerType.ENERGY: [r"\benergy\b", r"\bpower\s*field\b", r"\baura\b"],
        VFXLayerType.ATMOSPHERIC: [r"\batmospheric\b", r"\baura\b", r"\bhaze\b"],
        VFXLayerType.DEBRIS: [r"\bdebris\b", r"\brubble\b", r"\bfragments\b"],
        VFXLayerType.CINEMATIC_PARTICLES: [r"\bparticles\b", r"\bdust\b", r"\bmotes\b"],
    }

    @staticmethod
    def analyze(prompt: str, source_asset_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        source_asset_context = source_asset_context or {}

        matched_operations = []
        for trans_type, patterns in TransformationAnalyzer.TRANSFORMATION_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    target = TransformationAnalyzer._extract_target(prompt_lower, trans_type)
                    params = TransformationAnalyzer._extract_parameters(prompt_lower, trans_type)
                    vfx_layers = TransformationAnalyzer._extract_vfx_layers(prompt_lower)
                    matched_operations.append(
                        TransformationOperation(
                            type=trans_type,
                            target=target,
                            parameters=params,
                            references=source_asset_context.get("reference_asset_ids", []),
                            preserve_identity=TransformationAnalyzer._detect_identity_preservation(prompt_lower),
                            preserve_background=TransformationAnalyzer._detect_background_preservation(prompt_lower, trans_type),
                            strength=TransformationAnalyzer._extract_strength(prompt_lower),
                            vfx_layers=vfx_layers,
                        )
                    )
                    break

        confidence = min(1.0, 0.5 + 0.1 * len(matched_operations))
        requires_clarification = len(matched_operations) == 0
        clarification_questions = []
        missing_capabilities = []
        warnings = []

        if requires_clarification:
            clarification_questions.append(
                "What would you like to transform in this video? Please describe the target object or area."
            )
        else:
            for op in matched_operations:
                caps = TransformationAnalyzer._required_capabilities(op.type)
                missing_capabilities.extend(caps)

        if len(matched_operations) > 1:
            warnings.append("Multiple transformations detected. They will be executed in sequence.")

        return {
            "suggested_operations": matched_operations,
            "confidence": confidence,
            "requires_clarification": requires_clarification,
            "clarification_questions": clarification_questions,
            "missing_capabilities": list(set(missing_capabilities)),
            "warnings": warnings,
        }

    @staticmethod
    def _extract_target(prompt: str, trans_type: TransformationType) -> TargetSelector:
        target_type = TargetSelectorType.OBJECT
        description = "unspecified target"

        for t_type, patterns in TransformationAnalyzer.TARGET_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, prompt, re.IGNORECASE)
                if match:
                    target_type = t_type
                    description = match.group(0)
                    break
            if target_type != TargetSelectorType.OBJECT:
                break

        if trans_type == TransformationType.BACKGROUND_REPLACEMENT:
            target_type = TargetSelectorType.BACKGROUND
            bg_match = re.search(r"\b(to|with|into)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b", prompt, re.IGNORECASE)
            if bg_match:
                description = f"Replace background with {bg_match.group(2)}"

        return TargetSelector(type=target_type, description=description, confidence=0.8)

    @staticmethod
    def _extract_parameters(prompt: str, trans_type: TransformationType) -> Dict[str, Any]:
        params: Dict[str, Any] = {}

        strength_match = re.search(r"\b(strength|intensity|amount)\s*[:\-]?\s*(\d+(?:\.\d+)?)\b", prompt, re.IGNORECASE)
        if strength_match:
            params["strength"] = float(strength_match.group(2))
        else:
            params["strength"] = 0.8

        seed_match = re.search(r"\bseed\s*[:\-]?\s*(\d+)\b", prompt, re.IGNORECASE)
        if seed_match:
            params["seed"] = int(seed_match.group(1))

        preserve_match = re.search(r"\bkeep\b.*?\b(same|exact|identical)\b", prompt, re.IGNORECASE)
        if preserve_match:
            params["preserve_mode"] = "exact"

        if trans_type == TransformationType.CAMERA_TRANSFORM:
            camera_match = re.search(r"\b(zoom|dolly|orbit|pan|tilt|tracking|crane|handheld|drone)\b", prompt, re.IGNORECASE)
            if camera_match:
                params["camera_movement"] = camera_match.group(1).lower()

        if trans_type == TransformationType.WEATHER_TRANSFORM:
            weather_match = re.search(r"\b(rain|snow|fog|storm|sunny|cloudy|clear)\b", prompt, re.IGNORECASE)
            if weather_match:
                params["weather"] = weather_match.group(1).lower()

        return params

    @staticmethod
    def _extract_vfx_layers(prompt: str) -> List[VFXLayer]:
        layers = []
        for vfx_type, patterns in TransformationAnalyzer.VFX_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    layers.append(VFXLayer(layer_type=vfx_type, intensity=1.0, opacity=0.9))
                    break
        return layers

    @staticmethod
    def _detect_identity_preservation(prompt: str) -> bool:
        patterns = [
            r"\bkeep\b.*?\b(same|exact|identical)\b",
            r"\bpreserve\b.*?\b(identity|face|character)\b",
            r"\bconsistent\b.*?\b(character|identity|face)\b",
            r"\bdo\s*not\s*change\b.*?\b(face|identity|character|clothes|hair)\b",
        ]
        return any(re.search(p, prompt, re.IGNORECASE) for p in patterns)

    @staticmethod
    def _detect_background_preservation(prompt: str, trans_type: TransformationType) -> bool:
        if trans_type == TransformationType.BACKGROUND_REPLACEMENT:
            return False
        patterns = [
            r"\bkeep\b.*?\bbackground\b.*?\b(same|unchanged|intact)\b",
            r"\bpreserve\b.*?\bbackground\b",
            r"\bdo\s*not\s*change\b.*?\bbackground\b",
        ]
        return any(re.search(p, prompt, re.IGNORECASE) for p in patterns)

    @staticmethod
    def _extract_strength(prompt: str) -> float:
        strength_match = re.search(r"\b(strength|intensity)\s*[:\-]?\s*(\d+(?:\.\d+)?)\b", prompt, re.IGNORECASE)
        if strength_match:
            val = float(strength_match.group(2))
            return max(0.0, min(1.0, val))
        return 0.8

    @staticmethod
    def _required_capabilities(trans_type: TransformationType) -> List[str]:
        capability_map = {
            TransformationType.OBJECT_REMOVAL: ["object_removal", "inpainting"],
            TransformationType.OBJECT_REPLACEMENT: ["object_replacement", "reference_images"],
            TransformationType.BACKGROUND_REPLACEMENT: ["background_replacement"],
            TransformationType.STYLE_TRANSFER: ["video_to_video"],
            TransformationType.MOTION_TRANSFER: ["motion_generation", "face_animation"],
            TransformationType.CAMERA_TRANSFORM: ["video_to_video"],
            TransformationType.VFX_APPLY: ["vfx_generation"],
            TransformationType.INPAINTING: ["inpainting"],
            TransformationType.OUTPAINTING: ["outpainting"],
            TransformationType.ENVIRONMENT_TRANSFORM: ["video_to_video"],
            TransformationType.ACTION_TRANSFORM: ["motion_generation"],
            TransformationType.LIGHTING_TRANSFORM: ["video_to_video"],
            TransformationType.WEATHER_TRANSFORM: ["video_to_video"],
            TransformationType.IDENTITY_PRESERVE: ["face_animation", "reference_images"],
            TransformationType.VIDEO_TO_VIDEO: ["video_to_video"],
        }
        return capability_map.get(trans_type, [])
