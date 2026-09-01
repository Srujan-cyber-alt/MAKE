from typing import Optional, Dict, Any, List
from app.schemas.phase7 import FrameRange


SOCIAL_PRESETS = {
    "youtube": {"aspect_ratio": "16:9", "resolution": "1920x1080", "fps": 30, "max_duration": 600},
    "instagram_feed": {"aspect_ratio": "1:1", "resolution": "1080x1080", "fps": 30, "max_duration": 60},
    "instagram_reel": {"aspect_ratio": "9:16", "resolution": "1080x1920", "fps": 30, "max_duration": 90},
    "tiktok": {"aspect_ratio": "9:16", "resolution": "1080x1920", "fps": 30, "max_duration": 180},
    "shorts": {"aspect_ratio": "9:16", "resolution": "1080x1920", "fps": 30, "max_duration": 60},
    "advertisement": {"aspect_ratio": "16:9", "resolution": "1920x1080", "fps": 30, "max_duration": 30},
    "cinematic": {"aspect_ratio": "21:9", "resolution": "2560x1080", "fps": 24, "max_duration": 300},
    "square": {"aspect_ratio": "1:1", "resolution": "1080x1080", "fps": 30, "max_duration": 60},
    "vertical": {"aspect_ratio": "9:16", "resolution": "1080x1920", "fps": 30, "max_duration": 180},
}


class SocialExportService:
    @staticmethod
    def get_preset(platform: str) -> Dict[str, Any]:
        return SOCIAL_PRESETS.get(platform, SOCIAL_PRESETS["youtube"])

    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        return [{"platform": k, **v} for k, v in SOCIAL_PRESETS.items()]

    @staticmethod
    def validate_against_preset(
        duration_seconds: Optional[float],
        width: Optional[int],
        height: Optional[int],
        fps: Optional[float],
        platform: str,
    ) -> Dict[str, Any]:
        preset = SocialExportService.get_preset(platform)
        issues = []

        if duration_seconds and duration_seconds > preset["max_duration"]:
            issues.append(f"Duration {duration_seconds}s exceeds platform limit {preset['max_duration']}s")

        if width and height:
            expected = preset["resolution"].split("x")
            if int(expected[0]) != width or int(expected[1]) != height:
                issues.append(f"Resolution {width}x{height} does not match preset {preset['resolution']}")

        if fps and fps != preset["fps"]:
            issues.append(f"FPS {fps} does not match preset {preset['fps']}")

        return {
            "valid": len(issues) == 0,
            "preset": preset,
            "issues": issues,
        }
