import os
import magic
from pathlib import Path
from typing import Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class FileValidationConfig:
    max_file_size_bytes: int = 100 * 1024 * 1024  # 100MB
    allowed_image_types: Set[str] = None
    allowed_video_types: Set[str] = None
    allowed_audio_types: Set[str] = None
    max_image_dimension: int = 8192
    max_video_dimension: int = 4096

    def __post_init__(self):
        if self.allowed_image_types is None:
            self.allowed_image_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if self.allowed_video_types is None:
            self.allowed_video_types = {"video/mp4", "video/quicktime", "video/webm", "video/avi"}
        if self.allowed_audio_types is None:
            self.allowed_audio_types = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"}


class FileValidationError(Exception):
    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message)
        self.code = code


class FileValidator:
    def __init__(self, config: Optional[FileValidationConfig] = None):
        self.config = config or FileValidationConfig()
        self._magic = None
        try:
            self._magic = magic.Magic(mime=True)
        except Exception:
            pass

    def validate(self, file_path: str, filename: str, content_type: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[dict]]:
        path = Path(file_path)
        if not path.exists():
            raise FileValidationError("File does not exist", code="file_not_found")
        file_size = path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            raise FileValidationError(
                f"File size {file_size} exceeds limit {self.config.max_file_size_bytes}",
                code="file_too_large",
            )
        if file_size == 0:
            raise FileValidationError("File is empty", code="empty_file")
        ext = path.suffix.lower()
        if not ext:
            raise FileValidationError("File has no extension", code="no_extension")
        detected_mime = self._detect_mime(file_path)
        if detected_mime and content_type and detected_mime != content_type:
            if not self._is_compatible(detected_mime, content_type):
                raise FileValidationError(
                    f"MIME type mismatch: declared {content_type}, detected {detected_mime}",
                    code="mime_mismatch",
                )
        asset_type = self._classify_asset_type(detected_mime or content_type or "", ext)
        metadata = {
            "detected_mime": detected_mime,
            "declared_mime": content_type,
            "extension": ext,
            "file_size_bytes": file_size,
            "asset_type": asset_type,
        }
        if asset_type == "image":
            if content_type not in self.config.allowed_image_types:
                raise FileValidationError(f"Image type {content_type} not allowed", code="unsupported_type")
        elif asset_type == "video":
            if content_type not in self.config.allowed_video_types:
                raise FileValidationError(f"Video type {content_type} not allowed", code="unsupported_type")
        elif asset_type == "audio":
            if content_type not in self.config.allowed_audio_types:
                raise FileValidationError(f"Audio type {content_type} not allowed", code="unsupported_type")
        else:
            raise FileValidationError(f"Unsupported file type: {content_type}", code="unsupported_type")
        return True, None, metadata

    def _detect_mime(self, file_path: str) -> Optional[str]:
        if self._magic:
            try:
                return self._magic.from_file(file_path)
            except Exception:
                pass
        return None

    def _is_compatible(self, detected: str, declared: str) -> bool:
        compatible = {
            "image/jpeg": {"image/jpg", "image/jpeg"},
            "image/png": {"image/png"},
            "video/mp4": {"video/mp4"},
            "video/quicktime": {"video/quicktime", "video/mov"},
        }
        return detected == declared or declared in compatible.get(detected, set())

    def _classify_asset_type(self, mime: str, ext: str) -> str:
        if mime.startswith("image/") or ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return "image"
        if mime.startswith("video/") or ext in {".mp4", ".mov", ".webm", ".avi"}:
            return "video"
        if mime.startswith("audio/") or ext in {".mp3", ".wav", ".ogg", ".m4a"}:
            return "audio"
        return "unknown"
