"""
Proxy System for MAKE AI Video Phase 17.

Proxy media for smooth editing of high-resolution footage.
"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ProxySystem:
    PROXY_PRESETS = {
        "4k_to_720p": {"source_resolution": (3840, 2160), "proxy_resolution": (1280, 720), "fps": 30, "codec": "libx264", "crf": 28},
        "4k_to_1080p": {"source_resolution": (3840, 2160), "proxy_resolution": (1920, 1080), "fps": 30, "codec": "libx264", "crf": 23},
        "1080p_to_720p": {"source_resolution": (1920, 1080), "proxy_resolution": (1280, 720), "fps": 30, "codec": "libx264", "crf": 28},
        "1080p_to_480p": {"source_resolution": (1920, 1080), "proxy_resolution": (854, 480), "fps": 30, "codec": "libx264", "crf": 30},
    }

    def get_proxy_preset(self, source_resolution: tuple) -> Optional[Dict[str, Any]]:
        for preset_name, preset in self.PROXY_PRESETS.items():
            if preset["source_resolution"] == source_resolution:
                return preset
        if source_resolution[0] >= 3840:
            return self.PROXY_PRESETS["4k_to_720p"]
        elif source_resolution[0] >= 1920:
            return self.PROXY_PRESETS["1080p_to_720p"]
        return None

    def build_proxy_render_filter(self, preset: Dict[str, Any]) -> str:
        w, h = preset["proxy_resolution"]
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    def map_proxy_to_source(self, proxy_time: float, proxy_fps: int, source_fps: int) -> float:
        return proxy_time * (source_fps / proxy_fps)


proxy_system = ProxySystem()
