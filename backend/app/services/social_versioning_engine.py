"""
Social Versioning for MAKE AI Video Phase 17.

One master timeline generates platform-specific versions.
"""

from typing import Optional, Dict, List, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_REEL = "instagram_reel"
    TIKTOK = "tiktok"
    SHORTS = "shorts"
    LINKEDIN = "linkedin"
    X = "x"
    MASTER = "master"


class SocialVersion:
    def __init__(self, platform: Platform, timeline_id: str):
        self.platform = platform
        self.timeline_id = timeline_id
        self.aspect_ratio = self._get_aspect_ratio(platform)
        self.resolution = self._get_resolution(platform)
        self.max_duration = self._get_max_duration(platform)
        self.fps = 30

    def _get_aspect_ratio(self, platform: Platform) -> str:
        ratios = {
            Platform.YOUTUBE: "16:9",
            Platform.INSTAGRAM_FEED: "1:1",
            Platform.INSTAGRAM_REEL: "9:16",
            Platform.TIKTOK: "9:16",
            Platform.SHORTS: "9:16",
            Platform.LINKEDIN: "16:9",
            Platform.X: "16:9",
            Platform.MASTER: "16:9",
        }
        return ratios.get(platform, "16:9")

    def _get_resolution(self, platform: Platform) -> tuple:
        resolutions = {
            Platform.YOUTUBE: (1920, 1080),
            Platform.INSTAGRAM_FEED: (1080, 1080),
            Platform.INSTAGRAM_REEL: (1080, 1920),
            Platform.TIKTOK: (1080, 1920),
            Platform.SHORTS: (1080, 1920),
            Platform.LINKEDIN: (1920, 1080),
            Platform.X: (1920, 1080),
            Platform.MASTER: (1920, 1080),
        }
        return resolutions.get(platform, (1920, 1080))

    def _get_max_duration(self, platform: Platform) -> float:
        durations = {
            Platform.YOUTUBE: 600.0,
            Platform.INSTAGRAM_FEED: 60.0,
            Platform.INSTAGRAM_REEL: 90.0,
            Platform.TIKTOK: 180.0,
            Platform.SHORTS: 60.0,
            Platform.LINKEDIN: 600.0,
            Platform.X: 140.0,
            Platform.MASTER: 600.0,
        }
        return durations.get(platform, 600.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value,
            "timeline_id": self.timeline_id,
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "max_duration": self.max_duration,
            "fps": self.fps,
        }


class SocialVersioningEngine:
    def create_version(self, platform: Platform, timeline_id: str) -> SocialVersion:
        return SocialVersion(platform=platform, timeline_id=timeline_id)

    def generate_versions(self, master_timeline_id: str, platforms: List[Platform] = None) -> List[Dict[str, Any]]:
        platforms = platforms or [Platform.YOUTUBE, Platform.INSTAGRAM_REEL, Platform.TIKTOK, Platform.SHORTS]
        versions = []
        for platform in platforms:
            version = self.create_version(platform, master_timeline_id)
            versions.append(version.to_dict())
        return versions


social_versioning_engine = SocialVersioningEngine()
