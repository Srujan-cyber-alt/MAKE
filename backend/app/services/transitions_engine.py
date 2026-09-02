"""
Transitions Engine for MAKE AI Video Phase 17.

Structured transitions with FFmpeg xfade support.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TransitionType(str, Enum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE = "fade"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    DIP_TO_BLACK = "dip_to_black"
    DIP_TO_WHITE = "dip_to_white"
    WIPE = "wipe"
    SLIDE = "slide"
    PUSH = "push"
    ZOOM = "zoom"
    BLUR = "blur"
    WHIP = "whip"
    MATCH_CUT = "match_cut"


@dataclass
class Transition:
    transition_id: str
    transition_type: TransitionType
    duration: float
    from_clip_id: str
    to_clip_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    easing: str = "ease_in_out"


class TransitionsEngine:
    FFMPEG_XFADE_MAP = {
        TransitionType.CUT: "fade",
        TransitionType.DISSOLVE: "dissolve",
        TransitionType.FADE: "fade",
        TransitionType.FADE_IN: "fade",
        TransitionType.FADE_OUT: "fade",
        TransitionType.DIP_TO_BLACK: "fadeblack",
        TransitionType.DIP_TO_WHITE: "fadewhite",
        TransitionType.WIPE: "wipeleft",
        TransitionType.SLIDE: "slideleft",
        TransitionType.PUSH: "pushleft",
        TransitionType.ZOOM: "zoomin",
        TransitionType.BLUR: "blur",
        TransitionType.WHIP: "wipen",
        TransitionType.MATCH_CUT: "dissolve",
    }

    def create_transition(self, transition_type: TransitionType, duration: float, from_clip_id: str, to_clip_id: str, **kwargs) -> Transition:
        import uuid
        return Transition(
            transition_id=str(uuid.uuid4()),
            transition_type=transition_type,
            duration=duration,
            from_clip_id=from_clip_id,
            to_clip_id=to_clip_id,
            parameters=kwargs,
        )

    def get_ffmpeg_xfade_filter(self, transition: Transition, offset: float) -> str:
        xfade_type = self.FFMPEG_XFADE_MAP.get(transition.transition_type, "fade")
        return f"xfade=transition={xfade_type}:duration={transition.duration}:offset={offset}"

    def build_transition_chain(self, transitions: List[Transition], clip_durations: Dict[str, float]) -> str:
        if not transitions:
            return ""
        filters = []
        current_offset = 0.0
        for i, t in enumerate(transitions):
            if i == 0:
                current_offset = clip_durations.get(t.from_clip_id, 0) - t.duration
            else:
                current_offset += clip_durations.get(transitions[i-1].to_clip_id, 0)
            filters.append(self.get_ffmpeg_xfade_filter(t, current_offset))
            current_offset += t.duration
        return ",".join(filters)


transitions_engine = TransitionsEngine()
