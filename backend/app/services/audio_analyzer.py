import asyncio
from typing import Optional, Dict, Any, List
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
import logging

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    @staticmethod
    async def analyze_audio(asset_id: str, project_id: str, user_id: str) -> Dict[str, Any]:
        source_path = await AudioAnalyzer._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path:
            return {"error": "Asset not found"}

        try:
            info = await video_processing_service.inspect_media(source_path)
            has_audio = getattr(info, "audio_codec", None) is not None
            return {
                "has_audio": has_audio,
                "audio_codec": getattr(info, "audio_codec", None),
                "duration": getattr(info, "duration_seconds", None),
                "sample_rate": getattr(info, "audio_sample_rate", None),
                "analysis": {
                    "dialogue_detected": False,
                    "music_detected": False,
                    "sfx_detected": False,
                    "silence_segments": [],
                    "loudness": "normal",
                },
                "note": "Full audio intelligence requires librosa/pydub integration.",
            }
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return {"error": str(e), "has_audio": False}

    @staticmethod
    async def detect_speech(asset_id: str, project_id: str, user_id: str) -> Dict[str, Any]:
        return {
            "speech_detected": False,
            "segments": [],
            "note": "Speech detection requires Whisper or similar ASR model.",
        }

    @staticmethod
    async def normalize_audio(asset_id: str, project_id: str, user_id: str) -> Dict[str, Any]:
        source_path = await AudioAnalyzer._resolve_asset_path(asset_id, project_id, user_id)
        if not source_path or not video_processing_service._check_ffmpeg():
            return {"error": "Asset not found or ffmpeg unavailable"}
        output_path = f"/tmp/audio_normalized_{asset_id}.mp4"
        try:
            await video_processing_service.remove_audio(source_path, output_path)
            return {"output_path": output_path, "note": "Audio removed (normalization placeholder)."}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None
