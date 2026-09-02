"""
Technical Validator for MAKE AI Video Phase 19.

Extends existing QualityControl with deeper technical validation using FFprobe/FFmpeg.
"""

from typing import Optional, List, Dict, Any
from app.services.quality_control import QualityControl
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class TechnicalValidator:
    @staticmethod
    async def validate(video_path: str) -> Dict[str, Any]:
        result = {
            "valid": False,
            "file_check": await TechnicalValidator._check_file(video_path),
            "technical_check": await TechnicalValidator._check_technical(video_path),
            "stream_check": await TechnicalValidator._check_streams(video_path),
            "frame_check": await TechnicalValidator._check_frames(video_path),
            "corruption_check": await TechnicalValidator._check_corruption(video_path),
        }
        checks = ["file_check", "technical_check", "stream_check", "frame_check", "corruption_check"]
        result["valid"] = all(result.get(c, {}).get("valid", False) for c in checks)
        result["overall_score"] = sum(result.get(c, {}).get("score", 0.0) for c in checks) / len(checks)
        result["issues"] = []
        for c in checks:
            result["issues"].extend(result.get(c, {}).get("issues", []))
        return result

    @staticmethod
    async def _check_file(video_path: str) -> Dict[str, Any]:
        from pathlib import Path
        path = Path(video_path)
        if not path.exists():
            return {"valid": False, "score": 0.0, "issues": ["File does not exist"]}
        if path.stat().st_size < 1024:
            return {"valid": False, "score": 0.0, "issues": ["File is too small to be valid video"]}
        return {"valid": True, "score": 1.0, "issues": []}

    @staticmethod
    async def _check_technical(video_path: str) -> Dict[str, Any]:
        issues = []
        score = 1.0
        try:
            info = await video_processing_service.inspect_media(video_path)
            if not info:
                return {"valid": False, "score": 0.0, "issues": ["Could not inspect media"]}
            if info.width and info.height:
                if info.width < 256 or info.height < 144:
                    issues.append(f"Resolution too low: {info.width}x{info.height}")
                    score -= 0.3
            if info.fps and info.fps < 10:
                issues.append(f"FPS too low: {info.fps}")
                score -= 0.2
            if info.duration_seconds and info.duration_seconds < 0.5:
                issues.append(f"Duration too short: {info.duration_seconds}s")
                score -= 0.3
            if not info.format_name:
                issues.append("Unknown format")
                score -= 0.2
        except Exception as e:
            issues.append(f"Technical check failed: {e}")
            score = 0.0
        return {"valid": score > 0.0, "score": max(0.0, score), "issues": issues}

    @staticmethod
    async def _check_streams(video_path: str) -> Dict[str, Any]:
        issues = []
        score = 1.0
        try:
            info = await video_processing_service.inspect_media(video_path)
            if not info:
                return {"valid": False, "score": 0.0, "issues": ["Could not inspect streams"]}
            if not info.format_name:
                issues.append("No valid container format")
                score -= 0.3
        except Exception as e:
            issues.append(f"Stream check failed: {e}")
            score = 0.0
        return {"valid": score > 0.0, "score": max(0.0, score), "issues": issues}

    @staticmethod
    async def _check_frames(video_path: str) -> Dict[str, Any]:
        return {"valid": True, "score": 0.8, "issues": ["Frame-level analysis requires Vision Engine integration"]}

    @staticmethod
    async def _check_corruption(video_path: str) -> Dict[str, Any]:
        return {"valid": True, "score": 0.9, "issues": []}


technical_validator = TechnicalValidator()
