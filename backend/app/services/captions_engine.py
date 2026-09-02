"""
Captions Engine Upgrade for MAKE AI Video Phase 17.

Transcript-aware editing, burn-in, styles, and word-level timing.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CaptionStyle(str, Enum):
    CLEAN = "clean"
    CINEMATIC = "cinematic"
    SOCIAL = "social"
    BOLD = "bold"
    KARAOKE = "karaoke"


class CaptionFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    BURN_IN = "burn_in"


@dataclass
class CaptionSegment:
    segment_id: str
    start_time: float
    end_time: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    style: CaptionStyle = CaptionStyle.CLEAN
    position: str = "bottom"
    font: str = "Arial"
    size: int = 24
    color: str = "#FFFFFF"
    background: str = "#00000080"


@dataclass
class CaptionTrack:
    track_id: str
    language: str
    segments: List[CaptionSegment] = field(default_factory=list)
    style: CaptionStyle = CaptionStyle.CLEAN
    burn_in: bool = False


class CaptionsEngine:
    def create_track(self, language: str = "en", style: CaptionStyle = CaptionStyle.CLEAN) -> CaptionTrack:
        import uuid
        return CaptionTrack(
            track_id=str(uuid.uuid4()),
            language=language,
            style=style,
        )

    def add_segment(self, track: CaptionTrack, start_time: float, end_time: float, text: str, **kwargs) -> CaptionSegment:
        import uuid
        segment = CaptionSegment(
            segment_id=str(uuid.uuid4()),
            start_time=start_time,
            end_time=end_time,
            text=text,
            style=track.style,
            **kwargs,
        )
        track.segments.append(segment)
        return segment

    def export_srt(self, track: CaptionTrack) -> str:
        lines = []
        for i, segment in enumerate(track.segments, 1):
            start = self._format_time_srt(segment.start_time)
            end = self._format_time_srt(segment.end_time)
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        return "\n".join(lines)

    def export_vtt(self, track: CaptionTrack) -> str:
        lines = ["WEBVTT", ""]
        for segment in track.segments:
            start = self._format_time_vtt(segment.start_time)
            end = self._format_time_vtt(segment.end_time)
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        return "\n".join(lines)

    def build_burn_in_filter(self, track: CaptionTrack, video_width: int = 1920, video_height: int = 1080) -> str:
        filters = []
        for segment in track.segments:
            start = segment.start_time
            end = segment.end_time
            enable = f"enable='between(t\\,{start}\\,{end})'"
            y_pos = video_height - 80 if segment.position == "bottom" else 40
            font_color = segment.color.replace("#", "0x")
            bg_color = segment.background.replace("#", "0x")
            filters.append(
                f"drawtext=text='{segment.text}':fontsize={segment.size}:fontcolor={font_color}:"
                f"box=1:boxcolor={bg_color}:boxborderw=10:"
                f"x=(w-text_w)/2:y={y_pos}:{enable}"
            )
        return ",".join(filters) if filters else "null"

    def remove_filler_words(self, track: CaptionTrack, filler_words: List[str] = None) -> List[Dict[str, Any]]:
        filler_words = filler_words or ["um", "uh", "like", "you know", "basically", "actually"]
        removed = []
        new_segments = []
        for segment in track.segments:
            text_lower = segment.text.lower()
            if any(fw in text_lower for fw in filler_words):
                removed.append({
                    "segment_id": segment.segment_id,
                    "text": segment.text,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                })
            else:
                new_segments.append(segment)
        track.segments = new_segments
        return removed

    def _format_time_srt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")

    def _format_time_vtt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


captions_engine = CaptionsEngine()
