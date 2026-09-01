from typing import Optional, Dict, Any, List
from app.schemas.phase7 import FrameRange


class KeyframeEngine:
    @staticmethod
    def create_keyframe(
        parameter: str,
        frame: int,
        value: Any,
        interpolation: str = "linear",
    ) -> Dict[str, Any]:
        return {
            "parameter": parameter,
            "frame": frame,
            "value": value,
            "interpolation": interpolation,
        }

    @staticmethod
    def create_keyframe_sequence(
        parameter: str,
        start_frame: int,
        end_frame: int,
        start_value: Any,
        end_value: Any,
        interpolation: str = "linear",
    ) -> List[Dict[str, Any]]:
        return [
            KeyframeEngine.create_keyframe(parameter, start_frame, start_value, interpolation),
            KeyframeEngine.create_keyframe(parameter, end_frame, end_value, interpolation),
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
            if isinstance(prev["value"], (int, float)) and isinstance(next["value"], (int, float)):
                return prev["value"] + (next["value"] - prev["value"]) * t
            return prev["value"] if t < 0.5 else next["value"]
        return prev["value"] if prev else None

    @staticmethod
    def parse_natural_language_keyframes(prompt: str, frame_range: FrameRange) -> List[Dict[str, Any]]:
        keyframes = []
        if "grow" in prompt.lower() or "larger" in prompt.lower():
            start = frame_range.start_frame or 0
            end = frame_range.end_frame or start + 30
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("scale", start, end, 0.5, 1.5))
        if "rotate" in prompt.lower() or "360" in prompt.lower():
            start = frame_range.start_frame or 0
            end = frame_range.end_frame or start + 30
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("rotation", start, end, 0, 360))
        if "move" in prompt.lower() or "camera" in prompt.lower():
            start = frame_range.start_frame or 0
            end = frame_range.end_frame or start + 30
            keyframes.extend(KeyframeEngine.create_keyframe_sequence("camera_x", start, end, 0, 100))
        return keyframes
