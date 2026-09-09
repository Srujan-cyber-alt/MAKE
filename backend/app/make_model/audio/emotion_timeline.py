"""
Time-keyed emotional timeline with interpolation and looping.

Stores a sequence of emotional keyframes.  Queries interpolate smoothly
between keyframes using configurable curves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.make_model.audio.continuous_emotion import ContinuousEmotion


# Curve names supported by EmotionTransition.
LINEAR = "linear"
SIGMOID = "sigmoid"
COSINE = "cosine"
CUBIC = "cubic"


def _ease(t: float, curve: str) -> float:
    t = max(0.0, min(1.0, t))
    if curve == LINEAR:
        return t
    if curve == SIGMOID:
        return 1.0 / (1.0 + math.exp(-12.0 * (t - 0.5)))
    if curve == COSINE:
        return (1.0 - math.cos(t * math.pi)) / 2.0
    if curve == CUBIC:
        return t * t * (3.0 - 2.0 * t)
    return t


@dataclass
class EmotionKeyframe:
    time: float
    emotion: ContinuousEmotion
    curve: str = LINEAR
    duration: Optional[float] = None  # optional hold duration


@dataclass
class EmotionTransition:
    """Smooth interpolation between two emotional states."""

    from_emotion: ContinuousEmotion
    to_emotion: ContinuousEmotion
    curve: str = LINEAR
    duration: float = 1.0

    def sample(self, t: float) -> ContinuousEmotion:
        """Sample emotion at time ``t`` (0 <= t <= duration)."""
        if self.duration <= 0:
            return self.to_emotion
        ratio = max(0.0, min(1.0, t / self.duration))
        eased = _ease(ratio, self.curve)
        return self.from_emotion.blend(self.to_emotion, weight=eased)


class EmotionTimeline:
    """Time-keyed emotional states with interpolation and looping."""

    def __init__(self, loop: bool = False) -> None:
        self.loop = loop
        self._keyframes: List[EmotionKeyframe] = []
        self._default_emotion = ContinuousEmotion.neutral()

    # ------------------------------------------------------------------
    # Keyframe management
    # ------------------------------------------------------------------
    def add_keyframe(
        self,
        time: float,
        emotion: ContinuousEmotion,
        curve: str = LINEAR,
        duration: Optional[float] = None,
    ) -> EmotionKeyframe:
        kf = EmotionKeyframe(time=time, emotion=emotion, curve=curve, duration=duration)
        self._keyframes.append(kf)
        self._keyframes.sort(key=lambda k: k.time)
        return kf

    def remove_keyframe(self, time: float) -> bool:
        before = len(self._keyframes)
        self._keyframes = [k for k in self._keyframes if k.time != time]
        return len(self._keyframes) != before

    def clear(self) -> None:
        self._keyframes.clear()

    @property
    def keyframes(self) -> List[EmotionKeyframe]:
        return list(self._keyframes)

    @property
    def duration(self) -> float:
        if not self._keyframes:
            return 0.0
        last = self._keyframes[-1]
        if last.duration is not None:
            return last.time + last.duration
        return last.time

    def set_default(self, emotion: ContinuousEmotion) -> None:
        self._default_emotion = emotion

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------
    def sample(self, time: float) -> ContinuousEmotion:
        if not self._keyframes:
            return self._default_emotion

        # Handle looping.
        duration = self.duration
        if self.loop and duration > 0:
            time = time % duration

        # Before first keyframe -> hold first emotion.
        if time <= self._keyframes[0].time:
            return self._keyframes[0].emotion

        # After last keyframe -> hold last emotion (unless looping).
        if time >= self._keyframes[-1].time:
            return self._keyframes[-1].emotion

        # Find surrounding keyframes.
        prev_kf = self._keyframes[0]
        next_kf = self._keyframes[0]
        for idx in range(len(self._keyframes) - 1):
            if self._keyframes[idx].time <= time <= self._keyframes[idx + 1].time:
                prev_kf = self._keyframes[idx]
                next_kf = self._keyframes[idx + 1]
                break

        span = next_kf.time - prev_kf.time
        if span <= 0:
            return prev_kf.emotion

        transition = EmotionTransition(
            from_emotion=prev_kf.emotion,
            to_emotion=next_kf.emotion,
            curve=next_kf.curve,
            duration=span,
        )
        return transition.sample(time - prev_kf.time)

    def sample_many(self, times: List[float]) -> List[ContinuousEmotion]:
        return [self.sample(t) for t in times]

    def to_dict(self) -> Dict:
        return {
            "loop": self.loop,
            "default": self._default_emotion.to_dict(),
            "keyframes": [
                {
                    "time": k.time,
                    "emotion": k.emotion.to_dict(),
                    "curve": k.curve,
                    "duration": k.duration,
                }
                for k in self._keyframes
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionTimeline":
        timeline = cls(loop=data.get("loop", False))
        if "default" in data:
            timeline.set_default(ContinuousEmotion.from_dict(data["default"]))
        for raw in data.get("keyframes", []):
            timeline.add_keyframe(
                time=raw["time"],
                emotion=ContinuousEmotion.from_dict(raw["emotion"]),
                curve=raw.get("curve", LINEAR),
                duration=raw.get("duration"),
            )
        return timeline