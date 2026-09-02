"""
Motion Graphics Engine for MAKE AI Video Phase 17.

Text, shapes, lower thirds, callouts, and kinetic typography.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MotionGraphicType(str, Enum):
    TEXT = "text"
    SHAPE = "shape"
    LOWER_THIRD = "lower_third"
    CALLOUT = "callout"
    LOGO = "logo"
    COUNTER = "counter"
    PROGRESS = "progress"
    CHART = "chart"


class AnimationType(str, Enum):
    FADE = "fade"
    SLIDE = "slide"
    SCALE = "scale"
    REVEAL = "reveal"
    TYPE_ON = "type_on"
    KINETIC = "kinetic"
    STAGGER = "stagger"


@dataclass
class MotionGraphic:
    graphic_id: str
    graphic_type: MotionGraphicType
    start_time: float
    duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationType = AnimationType.FADE
    animation_duration: float = 0.5
    position: str = "bottom"
    opacity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KineticTypography:
    typography_id: str
    text: str
    start_time: float
    duration: float
    words: List[Dict[str, Any]] = field(default_factory=list)
    style: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationType = AnimationType.TYPE_ON


class MotionGraphicsEngine:
    def create_graphic(self, graphic_type: MotionGraphicType, start_time: float, duration: float, **kwargs) -> MotionGraphic:
        import uuid
        return MotionGraphic(
            graphic_id=str(uuid.uuid4()),
            graphic_type=graphic_type,
            start_time=start_time,
            duration=duration,
            **kwargs,
        )

    def create_kinetic_typography(self, text: str, start_time: float, duration: float, words: List[Dict[str, Any]] = None, **kwargs) -> KineticTypography:
        import uuid
        return KineticTypography(
            typography_id=str(uuid.uuid4()),
            text=text,
            start_time=start_time,
            duration=duration,
            words=words or [],
            **kwargs,
        )

    def build_drawtext_filter(self, graphic: MotionGraphic, video_width: int = 1920, video_height: int = 1080) -> str:
        params = graphic.parameters
        text = params.get("text", "")
        fontsize = params.get("font_size", 48)
        fontcolor = params.get("color", "white")
        bg = params.get("background", "black")
        x_expr = self._resolve_position(graphic.position, video_width, video_height)
        enable = f"enable='between(t\\,{graphic.start_time}\\,{graphic.start_time + graphic.duration})'"
        return f"drawtext=text='{text}':fontsize={fontsize}:fontcolor={fontcolor}:box=1:boxcolor={bg}@0.5:boxborderw=10:{x_expr}:{enable}"

    def _resolve_position(self, position: str, width: int, height: int) -> str:
        positions = {
            "top": f"y=40:x=(w-text_w)/2",
            "bottom": f"y={height - 80}:x=(w-text_w)/2",
            "center": f"y=(h-text_h)/2:x=(w-text_w)/2",
            "left": f"y=(h-text_h)/2:x=40",
            "right": f"y=(h-text_h)/2:x={width - 40}",
        }
        return positions.get(position, positions["bottom"])


motion_graphics_engine = MotionGraphicsEngine()
