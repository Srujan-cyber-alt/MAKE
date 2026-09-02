"""
Advanced Keyframe Engine for MAKE AI Video Phase 17.

Supports multiple interpolation types, easing, and curves.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class InterpolationType(str, Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    HOLD = "hold"
    BEZIER = "bezier"
    B_SPLINE = "b_spline"
    STEP = "step"


@dataclass
class Keyframe:
    keyframe_id: str
    clip_id: str
    parameter: str
    frame: int
    value: Any
    interpolation: InterpolationType = InterpolationType.LINEAR
    easing: str = "ease_in_out"
    bezier_handles: Optional[Dict[str, Any]] = None


@dataclass
class KeyframeSequence:
    sequence_id: str
    clip_id: str
    parameter: str
    keyframes: List[Keyframe] = field(default_factory=list)


class AdvancedKeyframeEngine:
    def create_keyframe(self, clip_id: str, parameter: str, frame: int, value: Any, interpolation: InterpolationType = InterpolationType.LINEAR, easing: str = "ease_in_out") -> Keyframe:
        import uuid
        return Keyframe(
            keyframe_id=str(uuid.uuid4()),
            clip_id=clip_id,
            parameter=parameter,
            frame=frame,
            value=value,
            interpolation=interpolation,
            easing=easing,
        )

    def create_keyframe_sequence(self, clip_id: str, parameter: str, start_frame: int, end_frame: int, start_value: Any, end_value: Any, interpolation: InterpolationType = InterpolationType.LINEAR, easing: str = "ease_in_out") -> KeyframeSequence:
        import uuid
        kf1 = Keyframe(
            keyframe_id=str(uuid.uuid4()),
            clip_id=clip_id,
            parameter=parameter,
            frame=start_frame,
            value=start_value,
            interpolation=interpolation,
            easing=easing,
        )
        kf2 = Keyframe(
            keyframe_id=str(uuid.uuid4()),
            clip_id=clip_id,
            parameter=parameter,
            frame=end_frame,
            value=end_value,
            interpolation=interpolation,
            easing=easing,
        )
        return KeyframeSequence(
            sequence_id=str(uuid.uuid4()),
            clip_id=clip_id,
            parameter=parameter,
            keyframes=[kf1, kf2],
        )

    def interpolate(self, keyframes: List[Keyframe], frame: int) -> Any:
        if not keyframes:
            return None
        sorted_kfs = sorted(keyframes, key=lambda k: k.frame)
        if frame <= sorted_kfs[0].frame:
            return sorted_kfs[0].value
        if frame >= sorted_kfs[-1].frame:
            return sorted_kfs[-1].value
        prev_kf = None
        next_kf = None
        for i, kf in enumerate(sorted_kfs):
            if kf.frame == frame:
                return kf.value
            if kf.frame < frame:
                prev_kf = kf
            if kf.frame > frame and next_kf is None:
                next_kf = kf
        if prev_kf is None or next_kf is None:
            return None
        t = (frame - prev_kf.frame) / (next_kf.frame - prev_kf.frame)
        t = self._apply_easing(t, prev_kf.easing)
        return self._interpolate_value(prev_kf.value, next_kf.value, t, prev_kf.interpolation)

    def _apply_easing(self, t: float, easing: str) -> float:
        if easing == "ease_in":
            return t * t
        elif easing == "ease_out":
            return t * (2 - t)
        elif easing == "ease_in_out":
            return t * t * (3 - 2 * t)
        elif easing == "ease_in_sine":
            import math
            return 1 - math.cos(t * math.pi / 2)
        elif easing == "ease_out_sine":
            import math
            return math.sin(t * math.pi / 2)
        return t

    def _interpolate_value(self, start: Any, end: Any, t: float, interpolation: InterpolationType) -> Any:
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            if interpolation == InterpolationType.HOLD:
                return start
            elif interpolation == InterpolationType.STEP:
                return start if t < 0.5 else end
            return start + (end - start) * t
        if isinstance(start, dict) and isinstance(end, dict):
            result = {}
            for key in start:
                result[key] = self._interpolate_value(start.get(key, 0), end.get(key, 0), t, interpolation)
            return result
        return start if t < 0.5 else end

    def parse_natural_language(self, prompt: str, start_frame: int, end_frame: int) -> List[Keyframe]:
        keyframes = []
        total_frames = end_frame - start_frame
        prompt_lower = prompt.lower()
        if "fade in" in prompt_lower or "fadein" in prompt_lower:
            keyframes.append(self.create_keyframe("", "opacity", start_frame, 0.0, InterpolationType.EASE_IN))
            keyframes.append(self.create_keyframe("", "opacity", start_frame + total_frames // 4, 1.0, InterpolationType.EASE_IN))
        elif "fade out" in prompt_lower or "fadeout" in prompt_lower:
            keyframes.append(self.create_keyframe("", "opacity", end_frame - total_frames // 4, 1.0, InterpolationType.EASE_OUT))
            keyframes.append(self.create_keyframe("", "opacity", end_frame, 0.0, InterpolationType.EASE_OUT))
        if "zoom in" in prompt_lower:
            keyframes.append(self.create_keyframe("", "scale", start_frame, 1.0, InterpolationType.EASE_IN))
            keyframes.append(self.create_keyframe("", "scale", end_frame, 1.3, InterpolationType.EASE_IN))
        elif "zoom out" in prompt_lower:
            keyframes.append(self.create_keyframe("", "scale", start_frame, 1.3, InterpolationType.EASE_OUT))
            keyframes.append(self.create_keyframe("", "scale", end_frame, 1.0, InterpolationType.EASE_OUT))
        if "slide" in prompt_lower or "move" in prompt_lower:
            keyframes.append(self.create_keyframe("", "position_x", start_frame, -100, InterpolationType.EASE_IN_OUT))
            keyframes.append(self.create_keyframe("", "position_x", end_frame, 100, InterpolationType.EASE_IN_OUT))
        return keyframes


advanced_keyframe_engine = AdvancedKeyframeEngine()
