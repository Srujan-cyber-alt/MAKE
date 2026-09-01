from typing import Optional, List, Dict, Any
from app.schemas.phase9 import KeyframeDefinition
import logging

logger = logging.getLogger(__name__)


class KeyframeSystemV2:
    @staticmethod
    def create_keyframe(
        parameter: str,
        frame: int,
        value: Any,
        interpolation: str = "linear",
        easing: Optional[str] = None,
    ) -> KeyframeDefinition:
        return KeyframeDefinition(
            parameter=parameter,
            frame=frame,
            value=value,
            interpolation=interpolation,
            easing=easing,
        )

    @staticmethod
    def create_keyframe_sequence(
        parameter: str,
        start_frame: int,
        end_frame: int,
        start_value: Any,
        end_value: Any,
        interpolation: str = "linear",
        easing: Optional[str] = None,
    ) -> List[KeyframeDefinition]:
        return [
            KeyframeSystemV2.create_keyframe(parameter, start_frame, start_value, interpolation, easing),
            KeyframeSystemV2.create_keyframe(parameter, end_frame, end_value, interpolation, easing),
        ]

    @staticmethod
    def interpolate(keyframes: List[KeyframeDefinition], frame: int) -> Optional[Any]:
        if not keyframes:
            return None
        sorted_kf = sorted(keyframes, key=lambda k: k.frame)
        prev = None
        next = None
        for kf in sorted_kf:
            if kf.frame <= frame:
                prev = kf
            elif kf.frame > frame and next is None:
                next = kf
                break
        if prev and next:
            t = (frame - prev.frame) / max(next.frame - prev.frame, 1)
            if isinstance(prev.value, (int, float)) and isinstance(next.value, (int, float)):
                return prev.value + (next.value - prev.value) * t
            return prev.value if t < 0.5 else next.value
        return prev.value if prev else None

    @staticmethod
    def parse_natural_language(prompt: str, frame_range_start: int = 0, frame_range_end: int = 30) -> List[KeyframeDefinition]:
        keyframes = []
        prompt_lower = prompt.lower()
        start = frame_range_start
        end = frame_range_end

        if "grow" in prompt_lower or "larger" in prompt_lower or "bigger" in prompt_lower:
            keyframes.extend(KeyframeSystemV2.create_keyframe_sequence("scale", start, end, 0.5, 1.5, "ease_in_out"))
        if "shrink" in prompt_lower or "smaller" in prompt_lower:
            keyframes.extend(KeyframeSystemV2.create_keyframe_sequence("scale", start, end, 1.5, 0.5, "ease_in_out"))
        if "rotate" in prompt_lower or "360" in prompt_lower:
            keyframes.extend(KeyframeSystemV2.create_keyframe_sequence("rotation", start, end, 0, 360, "linear"))
        if "move" in prompt_lower and "camera" in prompt_lower:
            keyframes.extend(KeyframeSystemV2.create_keyframe_sequence("camera_x", start, end, 0, 100, "ease_in_out"))
        if "fade in" in prompt_lower:
            keyframes.append(KeyframeSystemV2.create_keyframe("opacity", start, 0.0, "ease_in"))
            keyframes.append(KeyframeSystemV2.create_keyframe("opacity", start + 10, 1.0, "ease_in"))
        if "fade out" in prompt_lower:
            keyframes.append(KeyframeSystemV2.create_keyframe("opacity", end - 10, 1.0, "ease_out"))
            keyframes.append(KeyframeSystemV2.create_keyframe("opacity", end, 0.0, "ease_out"))

        return keyframes
