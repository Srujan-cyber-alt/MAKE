import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple


class VideoProcessingError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class MediaInfo:
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec_name: Optional[str] = None
    pixel_format: Optional[str] = None
    bit_rate: Optional[int] = None
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    file_size_bytes: Optional[int] = None
    format_name: Optional[str] = None


@dataclass
class ProcessingResult:
    output_path: str
    media_info: MediaInfo
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VideoProcessingService:
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "makeai-video"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._ffmpeg_available = None
        self._ffprobe_available = None

    def _check_ffmpeg(self) -> bool:
        if self._ffmpeg_available is None:
            self._ffmpeg_available = shutil.which("ffmpeg") is not None
        return self._ffmpeg_available

    def _check_ffprobe(self) -> bool:
        if self._ffprobe_available is None:
            self._ffprobe_available = shutil.which("ffprobe") is not None
        return self._ffprobe_available

    async def inspect_media(self, file_path: str) -> MediaInfo:
        if not self._check_ffprobe():
            raise VideoProcessingError("ffprobe is not available. Install FFmpeg to use video processing.")
        path = Path(file_path)
        if not path.exists():
            raise VideoProcessingError(f"File not found: {file_path}")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            data = json.loads(stdout.decode())
            info = MediaInfo(
                file_size_bytes=path.stat().st_size,
                format_name=data.get("format", {}).get("format_name"),
            )
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info.width = stream.get("width")
                    info.height = stream.get("height")
                    info.codec_name = stream.get("codec_name")
                    info.pixel_format = stream.get("pix_fmt")
                    info.bit_rate = int(stream.get("bit_rate", 0)) or None
                    fps_str = stream.get("r_frame_rate") or stream.get("avg_frame_rate")
                    if fps_str and "/" in fps_str:
                        num, den = fps_str.split("/")
                        if int(den) > 0:
                            info.fps = int(num) / int(den)
                elif stream.get("codec_type") == "audio":
                    info.audio_codec = stream.get("codec_name")
                    info.audio_sample_rate = int(stream.get("sample_rate", 0)) or None
            if info.duration_seconds is None:
                dur = data.get("format", {}).get("duration")
                if dur:
                    info.duration_seconds = float(dur)
            return info
        except asyncio.TimeoutError:
            raise VideoProcessingError("FFprobe timed out")
        except json.JSONDecodeError:
            raise VideoProcessingError("Invalid FFprobe output")
        except Exception as e:
            raise VideoProcessingError(f"FFprobe failed: {e}")

    async def trim(self, input_path: str, start_seconds: float, end_seconds: float, output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        output_path = output_path or str(self.temp_dir / f"trim_{Path(input_path).name}")
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(start_seconds), "-to", str(end_seconds),
            "-c", "copy", output_path,
        ]
        await self._run_ffmpeg(cmd, output_path)
        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def cut(self, input_path: str, start_seconds: float, end_seconds: float, output_path: Optional[str] = None) -> ProcessingResult:
        return await self.trim(input_path, start_seconds, end_seconds, output_path)

    async def concatenate(self, input_paths: List[str], output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        if not input_paths:
            raise VideoProcessingError("No input files provided")
        output_path = output_path or str(self.temp_dir / f"concat_{Path(input_paths[0]).name}")
        list_file = self.temp_dir / "concat_list.txt"
        with open(list_file, "w") as f:
            for path in input_paths:
                f.write(f"file '{path}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output_path,
        ]
        await self._run_ffmpeg(cmd, output_path)
        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def resize(self, input_path: str, width: int, height: int, output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        output_path = output_path or str(self.temp_dir / f"resize_{Path(input_path).name}")
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "copy", output_path,
        ]
        await self._run_ffmpeg(cmd, output_path)
        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def change_aspect_ratio(self, input_path: str, aspect_ratio: str, output_path: Optional[str] = None) -> ProcessingResult:
        w, h = aspect_ratio.split(":")
        return await self.resize(input_path, int(w), int(h), output_path)

    async def extract_thumbnail(self, input_path: str, timestamp_seconds: float = 1.0, output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        output_path = output_path or str(self.temp_dir / f"thumb_{Path(input_path).stem}.jpg")
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(timestamp_seconds), "-vframes", "1",
            "-q:v", "2", output_path,
        ]
        await self._run_ffmpeg(cmd, output_path)
        file_size = Path(output_path).stat().st_size
        media_info = MediaInfo(file_size_bytes=file_size)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def change_speed(self, input_path: str, speed_factor: float, output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        output_path = output_path or str(self.temp_dir / f"speed_{Path(input_path).name}")
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-filter:v", f"setpts={1/speed_factor}*PTS",
            "-filter:a", f"atempo={speed_factor}",
            output_path,
        ]
        await self._run_ffmpeg(cmd, output_path)
        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def remove_audio(self, input_path: str, output_path: Optional[str] = None) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("ffmpeg is not available")
        output_path = output_path or str(self.temp_dir / f"mute_{Path(input_path).name}")
        cmd = ["ffmpeg", "-y", "-i", input_path, "-an", "-c:v", "copy", output_path]
        await self._run_ffmpeg(cmd, output_path)
        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)

    async def _run_ffmpeg(self, cmd: List[str], output_path: str) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            if proc.returncode != 0:
                error_msg = stderr.decode()[-1000:] if stderr else "Unknown error"
                raise VideoProcessingError(f"FFmpeg failed with code {proc.returncode}", details={"stderr": error_msg})
            if not Path(output_path).exists():
                raise VideoProcessingError("FFmpeg completed but output file is missing")
        except asyncio.TimeoutError:
            raise VideoProcessingError("FFmpeg timed out")

    async def apply_filter(self, input_path: str, filter_str: str, output_path: str) -> ProcessingResult:
        if not self._check_ffmpeg():
            raise VideoProcessingError("FFmpeg is not available")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-filter_complex", filter_str,
            "-c:a", "copy",
            output_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            if proc.returncode != 0:
                error_msg = stderr.decode()[-1000:] if stderr else "Unknown error"
                raise VideoProcessingError(f"FFmpeg filter failed with code {proc.returncode}", details={"stderr": error_msg})
            if not Path(output_path).exists():
                raise VideoProcessingError("FFmpeg filter completed but output file is missing")
        except asyncio.TimeoutError:
            raise VideoProcessingError("FFmpeg filter timed out")

        media_info = await self.inspect_media(output_path)
        return ProcessingResult(output_path=output_path, media_info=media_info, success=True)


video_processing_service = VideoProcessingService()
