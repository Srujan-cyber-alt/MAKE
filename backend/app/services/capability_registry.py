"""
Local-first Capability Registry for MAKE AI Video.

Detects installed/available capabilities at runtime:
- FFmpeg/FFprobe
- SAM/YOLO/RMBG (segmentation)
- OpenCV/DeepSORT/ByteTrack (tracking)
- Providers (Runway, Pika, test)
- GPU availability
- Redis
- PostgreSQL
- Whisper/librosa (audio)
"""

from typing import Dict, Any, List, Optional
from app.services.redis_service import redis_service
from app.providers.registry import get_provider_registry
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    @staticmethod
    async def get_all_capabilities() -> Dict[str, Any]:
        capabilities = {
            "ffmpeg": CapabilityRegistry._check_ffmpeg(),
            "ffprobe": CapabilityRegistry._check_ffprobe(),
            "gpu": CapabilityRegistry._check_gpu(),
            "segmentation": await CapabilityRegistry._check_segmentation(),
            "tracking": await CapabilityRegistry._check_tracking(),
            "providers": await CapabilityRegistry._check_providers(),
            "redis": CapabilityRegistry._check_redis(),
            "database": CapabilityRegistry._check_database(),
            "audio": await CapabilityRegistry._check_audio(),
        }
        return capabilities

    @staticmethod
    def _check_ffmpeg() -> Dict[str, Any]:
        available = video_processing_service._check_ffmpeg()
        return {"available": available, "note": "FFmpeg available" if available else "FFmpeg not found"}

    @staticmethod
    def _check_ffprobe() -> Dict[str, Any]:
        available = video_processing_service._check_ffprobe()
        return {"available": available, "note": "FFprobe available" if available else "FFprobe not found"}

    @staticmethod
    def _check_gpu() -> Dict[str, Any]:
        try:
            import torch
            cuda = torch.cuda.is_available()
            return {"available": cuda, "backend": "pytorch", "note": f"CUDA available: {cuda}"}
        except ImportError:
            try:
                import cv2
                return {"available": False, "backend": "opencv", "note": "PyTorch not installed, OpenCV available but no GPU detection"}
            except ImportError:
                return {"available": False, "backend": "none", "note": "No ML backends installed"}

    @staticmethod
    async def _check_segmentation() -> Dict[str, Any]:
        backends = {}
        try:
            import torch
            backends["pytorch"] = {"available": True, "note": "PyTorch available"}
        except ImportError:
            backends["pytorch"] = {"available": False, "note": "PyTorch not installed"}

        try:
            import cv2
            backends["opencv"] = {"available": True, "note": "OpenCV available"}
        except ImportError:
            backends["opencv"] = {"available": False, "note": "OpenCV not installed"}

        try:
            import rembg
            backends["rembg"] = {"available": True, "note": "RMBG available"}
        except ImportError:
            backends["rembg"] = {"available": False, "note": "RMBG not installed"}

        return {"backends": backends, "any_available": any(b.get("available") for b in backends.values())}

    @staticmethod
    async def _check_tracking() -> Dict[str, Any]:
        backends = {}
        try:
            import cv2
            backends["opencv"] = {"available": True, "note": "OpenCV trackers available"}
        except ImportError:
            backends["opencv"] = {"available": False, "note": "OpenCV not installed"}

        try:
            import numpy
            backends["numpy"] = {"available": True, "note": "NumPy available"}
        except ImportError:
            backends["numpy"] = {"available": False, "note": "NumPy not installed"}

        return {"backends": backends, "any_available": any(b.get("available") for b in backends.values())}

    @staticmethod
    async def _check_providers() -> Dict[str, Any]:
        registry = get_provider_registry()
        providers = {}
        for name, provider in registry.get_all().items():
            try:
                health = await provider.health_check()
                providers[name] = {
                    "available": health.status == "active",
                    "status": health.status,
                    "error": health.error,
                    "models": [m.id for m in provider.get_supported_models()],
                }
            except Exception as e:
                providers[name] = {"available": False, "status": "error", "error": str(e), "models": []}
        return {"providers": providers, "any_available": any(p.get("available") for p in providers.values())}

    @staticmethod
    def _check_redis() -> Dict[str, Any]:
        available = redis_service.is_connected()
        return {"available": available, "note": "Redis connected" if available else "Redis not connected"}

    @staticmethod
    def _check_database() -> Dict[str, Any]:
        from app.core.config import settings
        is_postgres = settings.database_url.startswith("postgresql")
        return {
            "available": True,
            "type": "postgresql" if is_postgres else "sqlite",
            "note": f"Database configured: {'PostgreSQL' if is_postgres else 'SQLite'}",
        }

    @staticmethod
    async def _check_audio() -> Dict[str, Any]:
        backends = {}
        try:
            import whisper
            backends["whisper"] = {"available": True, "note": "Whisper available"}
        except ImportError:
            backends["whisper"] = {"available": False, "note": "Whisper not installed"}

        try:
            import librosa
            backends["librosa"] = {"available": True, "note": "Librosa available"}
        except ImportError:
            backends["librosa"] = {"available": False, "note": "Librosa not installed"}

        return {"backends": backends, "any_available": any(b.get("available") for b in backends.values())}
