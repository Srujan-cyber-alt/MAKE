import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from app.services.video_processing import VideoProcessingService


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    media_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ResultValidator:
    def __init__(self):
        self.video_service = VideoProcessingService()

    async def validate_output(self, file_path: str, expected_duration: float = None, expected_width: int = None, expected_height: int = None) -> ValidationResult:
        errors = []
        warnings = []

        if not file_path or not os.path.exists(file_path):
            return ValidationResult(valid=False, errors=["Output file does not exist"])

        try:
            media_info = await self.video_service.inspect_media(file_path)
        except Exception as e:
            return ValidationResult(valid=False, errors=[f"Failed to inspect media: {str(e)}"])

        if media_info.duration_seconds is None or media_info.duration_seconds <= 0:
            errors.append("Invalid or missing duration")

        if expected_duration is not None:
            if media_info.duration_seconds is None:
                errors.append(f"Expected duration {expected_duration}s but got None")
            elif abs(media_info.duration_seconds - expected_duration) > expected_duration * 0.5:
                warnings.append(f"Duration {media_info.duration_seconds}s differs significantly from expected {expected_duration}s")

        if media_info.width is None or media_info.height is None:
            errors.append("Invalid or missing resolution")
        elif media_info.width < 256 or media_info.height < 256:
            errors.append(f"Resolution too small: {media_info.width}x{media_info.height}")

        if expected_width and media_info.width and abs(media_info.width - expected_width) > expected_width * 0.3:
            warnings.append(f"Width {media_info.width} differs from expected {expected_width}")

        if expected_height and media_info.height and abs(media_info.height - expected_height) > expected_height * 0.3:
            warnings.append(f"Height {media_info.height} differs from expected {expected_height}")

        if media_info.fps is None or media_info.fps <= 0:
            errors.append("Invalid or missing frame rate")
        elif media_info.fps < 1 or media_info.fps > 120:
            warnings.append(f"Unusual FPS: {media_info.fps}")

        if media_info.file_size_bytes is not None and media_info.file_size_bytes < 1024:
            warnings.append("File size is suspiciously small")

        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            media_info={
                "duration_seconds": media_info.duration_seconds,
                "width": media_info.width,
                "height": media_info.height,
                "fps": media_info.fps,
                "codec_name": media_info.codec_name,
                "format_name": media_info.format_name,
                "file_size_bytes": media_info.file_size_bytes,
            },
        )
