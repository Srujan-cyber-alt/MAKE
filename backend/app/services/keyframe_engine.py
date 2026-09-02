from typing import Optional, Dict, Any, List, Tuple
from app.schemas.phase7 import FrameRange
import math


class InterpolationType:
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    HOLD = "hold"
    BEZIER = "bezier"
    STEP = "step"


class KeyframeEngine:
    @staticmethod
    def create_keyframe(
        parameter: str,
        frame: int,
        value: Any,
        interpolation: str = "linear",
        easing: str = "ease_in_out",
    ) -> Dict[str, Any]:
        return {
            "parameter": parameter,
            "frame": frame,
            "value": value,
            "interpolation": interpolation,
            "easing": easing,
        }

    @staticmethod
    def create_keyframe_sequence(
        parameter: str,
        start_frame: int,
        end_frame: int,
        start_value: Any,
        end_value: Any,
        interpolation: str = "linear",
        easing: str = "ease_in_out",
    ) -> List[Dict[str, Any]]:
        return [
            KeyframeEngine.create_keyframe(parameter, start_frame, start_value, interpolation, easing),
            KeyframeEngine.create_keyframe(parameter, end_frame, end_value, interpolation, easing),
        ]

    @staticmethod
    def interpolate_keyframes(
        keyframes: List[Dict[str, Any]],
        frame: int,
    ) -> Optional[Any]:
        if not keyframes:
            return None
        sorted_kf = sorted(keyframes, key=lambda k: k["frame"])
        prev = None
        next = None
        for kf in sorted_kf:
            if kf["frame"] <= frame:
                prev = kf
            elif kf["frame"] > frame and next is None:
                next = kf
                break
        if prev and next:
            t = (frame - prev["frame"]) / max(next["frame"] - prev["frame"], 1)
            easing = prev.get("easing", "ease_in_out")
            t = KeyframeEngine._apply_easing(t, easing)
            interpolation = prev.get("interpolation", "linear")
            if interpolation == InterpolationType.HOLD:
                return prev["value"]
            if interpolation == InterpolationType.STEP:
                return prev["value"] if t < 0.5 else next["value"]
            if isinstance(prev["value"], (int, float)) and isinstance(next["value"], (int, float)):
                return prev["value"] + (next["value"] - prev["value"]) * t
            return prev["value"] if t < 0.5 else next["value"]
        return prev["value"] if prev else None

    @staticmethod
    def _apply_easing(t: float, easing: str) -> float:
        if easing == "ease_in":
            return t * t
        elif easing == "ease_out":
            return t * (2 - t)
        elif easing == "ease_in_out":
            return t * t * (3 - 2 * t)
        elif easing == "ease_in_sine":
            return 1 - math.cos(t * math.pi / 2)
        elif easing == "ease_out_sine":
            return math.sin(t * math.pi / 2)
        elif easing == "ease_in_out_sine":
            return -(math.cos(math.pi * t) - 1) / 2
        elif easing == "ease_in_quad":
            return t * t
        elif easing == "ease_out_quad":
            return t * (2 - t)
        elif easing == "ease_in_out_quad":
            return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t
        return t

    @staticmethod
    def parse_natural_language_keyframes(prompt: str, frame_range: FrameRange) -> List[Dict[str, Any]]:
        keyframes = []
        start = frame_range.start_frame or 0
        end = frame_range.end_frame or start + 30
        prompt_lower = prompt.lower()
        if "fade in" in prompt_lower or "fadein" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("opacity", start, start + (end - start) // 4, 0.0, 1.0, "linear", "ease_in"))
        elif "fade out" in prompt_lower or "fadeout" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("opacity", end - (end - start) // 4, end, 1.0, 0.0, "linear", "ease_out"))
        if "zoom in" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("scale", start, end, 1.0, 1.3, "linear", "ease_in"))
        elif "zoom out" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("scale", start, end, 1.3, 1.0, "linear", "ease_out"))
        if "slide" in prompt_lower or "move" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("position_x", start, end, -100, 100, "linear", "ease_in_out"))
        if "rotate" in prompt_lower or "360" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("rotation", start, end, 0, 360, "linear", "linear"))
        if "grow" in prompt_lower or "larger" in prompt_lower:
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("scale", start, end, 0.5, 1.5, "linear", "ease_out"))
        return keyframes
