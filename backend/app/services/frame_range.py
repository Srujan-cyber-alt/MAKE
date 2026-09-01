from typing import Optional, Dict, Any
from app.schemas.phase7 import FrameRange


class FrameRangeParser:
    @staticmethod
    def from_time_range(start_time: float, end_time: float, fps: float = 30.0) -> FrameRange:
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        return FrameRange(start_frame=start_frame, end_frame=end_frame, start_time=start_time, end_time=end_time)

    @staticmethod
    def from_prompt(prompt: str, fps: float = 30.0) -> FrameRange:
        import re
        time_pattern = re.compile(r"(\d{1,2}):(\d{2})")
        matches = time_pattern.findall(prompt)
        if len(matches) >= 2:
            start = int(matches[0][0]) * 60 + int(matches[0][1])
            end = int(matches[1][0]) * 60 + int(matches[1][1])
            return FrameRangeParser.from_time_range(start, end, fps)
        return FrameRange(all_frames=True)

    @staticmethod
    def from_scene(scene_index: int) -> FrameRange:
        return FrameRange(scene_index=scene_index)

    @staticmethod
    def to_ffmpeg_select(filter_range: FrameRange) -> str:
        if filter_range.all_frames:
            return ""
        parts = []
        if filter_range.start_frame is not None:
            end = filter_range.end_frame if filter_range.end_frame is not None else "N"
            parts.append(f"between(n\\\\,{filter_range.start_frame}\\\\,{end})")
        if filter_range.start_time is not None:
            end = filter_range.end_time if filter_range.end_time is not None else "N"
            parts.append(f"between(t\\\\,{filter_range.start_time}\\\\,{end})")
        return "".join(parts)
