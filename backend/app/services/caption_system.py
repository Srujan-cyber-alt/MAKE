from typing import Optional, List, Dict, Any
from app.schemas.phase9 import CaptionTrack
from app.schemas.phase8 import SpeechSegment
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class CaptionStyle:
    CLEAN = "clean"
    CINEMATIC = "cinematic"
    SOCIAL = "social"
    BOLD = "bold"
    KARAOKE = "karaoke"


class CaptionSystem:
    @staticmethod
    async def create_track(
        track_id: str,
        language: str = "en",
        segments: Optional[List[Dict[str, Any]]] = None,
        style: Optional[Dict[str, Any]] = None,
        burn_in: bool = False,
    ) -> CaptionTrack:
        return CaptionTrack(
            track_id=track_id,
            language=language,
            segments=segments or [],
            style=style or {},
            burn_in=burn_in,
        )

    @staticmethod
    async def transcribe_speech(asset_id: str, project_id: str, user_id: str) -> Dict[str, Any]:
        return {
            "transcription": [],
            "segments": [],
            "note": "Speech transcription requires Whisper or similar ASR model integration.",
            "status": "not_implemented",
        }

    @staticmethod
    async def generate_captions_from_prompt(prompt: str, duration_seconds: float) -> CaptionTrack:
        segments = []
        words = prompt.split()
        words_per_segment = 5
        segment_duration = duration_seconds / max(len(words) / words_per_segment, 1)
        for i in range(0, len(words), words_per_segment):
            segment_words = words[i:i + words_per_segment]
            segments.append({
                "start": i * segment_duration,
                "end": (i + words_per_segment) * segment_duration,
                "text": " ".join(segment_words),
            })
        return CaptionTrack(
            track_id="caption_auto",
            language="en",
            segments=segments,
            style={"font": "Arial", "size": 24, "color": "white", "background": "black"},
            burn_in=False,
        )

    @staticmethod
    async def export_srt(caption_track: CaptionTrack) -> str:
        lines = []
        for i, segment in enumerate(caption_track.segments, 1):
            start = CaptionSystem._format_time(segment.get("start", 0))
            end = CaptionSystem._format_time(segment.get("end", 0))
            text = segment.get("text", "")
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    @staticmethod
    async def export_vtt(caption_track: CaptionTrack) -> str:
        lines = ["WEBVTT\n"]
        for segment in caption_track.segments:
            start = CaptionSystem._format_time(segment.get("start", 0), vtt=True)
            end = CaptionSystem._format_time(segment.get("end", 0), vtt=True)
            text = segment.get("text", "")
            lines.append(f"{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    @staticmethod
    def build_burn_in_filter(caption_track: CaptionTrack, video_width: int = 1920, video_height: int = 1080) -> str:
        filters = []
        for segment in caption_track.segments:
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            enable = f"enable='between(t\\,{start}\\,{end})'"
            y_pos = video_height - 80
            font_color = "white"
            bg_color = "black@0.5"
            style = caption_track.style or {}
            if style.get("color"):
                font_color = style["color"]
            if style.get("background"):
                bg_color = style["background"]
            if style.get("position") == "top":
                y_pos = 40
            filters.append(
                f"drawtext=text='{segment.get('text', '')}':fontsize={style.get('size', 24)}:fontcolor={font_color}:"
                f"box=1:boxcolor={bg_color}:boxborderw=10:"
                f"x=(w-text_w)/2:y={y_pos}:{enable}"
            )
        return ",".join(filters) if filters else "null"

    @staticmethod
    def remove_filler_words(caption_track: CaptionTrack, filler_words: List[str] = None) -> List[Dict[str, Any]]:
        filler_words = filler_words or ["um", "uh", "like", "you know", "basically", "actually"]
        removed = []
        new_segments = []
        for segment in caption_track.segments:
            text_lower = segment.get("text", "").lower()
            if any(fw in text_lower for fw in filler_words):
                removed.append({
                    "segment_id": segment.get("segment_id", ""),
                    "text": segment.get("text", ""),
                    "start_time": segment.get("start", 0),
                    "end_time": segment.get("end", 0),
                })
            else:
                new_segments.append(segment)
        caption_track.segments = new_segments
        return removed

    @staticmethod
    def _format_time(seconds: float, vtt: bool = False) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if vtt:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")
