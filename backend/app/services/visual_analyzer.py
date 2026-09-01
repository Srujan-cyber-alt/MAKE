import asyncio
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from app.schemas.phase7 import (
    VideoAnalysis,
    MLBackendStatus,
    DetectedTarget,
    TargetCategory,
    VisualAnalyzerResponse,
)
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectedScene:
    index: int
    start_time: float
    end_time: Optional[float] = None
    shot_type: str = "medium"
    camera_movement: str = "static"
    confidence: float = 1.0


@dataclass
class DetectedObject:
    object_id: str
    category: str
    label: str
    confidence: float
    bbox: Dict[str, float]
    frame_number: int
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


class VisualAnalyzer:
    @staticmethod
    async def analyze_video(
        asset_id: str,
        project_id: str,
        user_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        max_frames: int = 30,
    ) -> Dict[str, Any]:
        cache_key = f"visual_analysis:{asset_id}:{hash(str(frame_range))}:{max_frames}"
        if redis_service.is_connected():
            cached = await redis_service.get_json(cache_key)
            if cached:
                return cached

        storage_path = await VisualAnalyzer._resolve_asset_path(asset_id, project_id, user_id)
        if not storage_path or not Path(storage_path).exists():
            return VisualAnalyzer._error_result("Asset file not found for visual analysis.")

        try:
            media_info = await video_processing_service.inspect_media(storage_path)
        except Exception as e:
            logger.warning(f"ffprobe inspection failed: {e}")
            media_info = None

        analysis = VideoAnalysis(
            duration_seconds=getattr(media_info, "duration_seconds", None) if media_info else None,
            resolution=(getattr(media_info, "width", None), getattr(media_info, "height", None)) if media_info else None,
            fps=getattr(media_info, "fps", None) if media_info else None,
            codec=getattr(media_info, "codec_name", None) if media_info else None,
            audio_codec=getattr(media_info, "audio_codec", None) if media_info else None,
            file_size_bytes=getattr(media_info, "file_size_bytes", None) if media_info else None,
            aspect_ratio=VisualAnalyzer._compute_aspect_ratio(media_info) if media_info else None,
            ml_available=VisualAnalyzer._detect_ml_backends(),
        )

        scene_changes = await VisualAnalyzer._detect_scene_changes(storage_path)
        analysis.scene_changes = scene_changes

        key_frames = await VisualAnalyzer._extract_key_frames(storage_path, scene_changes)
        analysis.key_frames = key_frames

        motion_vectors = await VisualAnalyzer._estimate_motion(storage_path)
        analysis.motion_vectors = motion_vectors

        objects, faces = await VisualAnalyzer._detect_targets_heuristic(media_info, storage_path)

        result = VisualAnalyzerResponse(
            analysis=analysis,
            objects=objects,
            faces=faces,
            scenes=[{"index": i, "time": t, "shot_type": "medium", "camera_movement": "static"} for i, t in enumerate(scene_changes)],
            motion={"vector_count": len(motion_vectors), "has_significant_motion": len(motion_vectors) > 3},
            ml_available={k: v == MLBackendStatus.AVAILABLE for k, v in analysis.ml_available.items()},
        )

        if redis_service.is_connected():
            await redis_service.set_json(cache_key, result.model_dump(), ex=3600)

        return result.model_dump()

    @staticmethod
    async def analyze_for_transformation(
        asset_id: str,
        project_id: str,
        user_id: str,
        prompt: str,
        frame_range: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        analysis = await VisualAnalyzer.analyze_video(asset_id, project_id, user_id, frame_range)
        targets = analysis.get("objects", []) + analysis.get("faces", [])
        target_selection = await SmartTargetSelector.select_target(
            prompt=prompt,
            detected_targets=targets,
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
        )
        return {
            "analysis": analysis,
            "targets": targets,
            "target_selection": target_selection.model_dump() if hasattr(target_selection, "model_dump") else target_selection,
        }

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None

    @staticmethod
    def _compute_aspect_ratio(media_info) -> Optional[str]:
        if not media_info or not media_info.width or not media_info.height:
            return None
        from math import gcd
        g = gcd(media_info.width, media_info.height)
        return f"{media_info.width // g}:{media_info.height // g}"

    @staticmethod
    def _detect_ml_backends() -> Dict[str, MLBackendStatus]:
        backends = {}
        try:
            import torch
            backends["pytorch"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["pytorch"] = MLBackendStatus.NOT_INSTALLED

        try:
            import cv2
            backends["opencv"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["opencv"] = MLBackendStatus.NOT_INSTALLED

        try:
            import transformers
            backends["transformers"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["transformers"] = MLBackendStatus.NOT_INSTALLED

        try:
            import rembg
            backends["rembg"] = MLBackendStatus.AVAILABLE
        except ImportError:
            backends["rembg"] = MLBackendStatus.NOT_INSTALLED

        return backends

    @staticmethod
    async def _detect_scene_changes(video_path: str) -> List[float]:
        if not video_processing_service._check_ffprobe():
            return []
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_pts_time,pict_type",
            "-of", "csv=p=0",
            video_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            timestamps = []
            prev_type = None
            for line in stdout.decode().strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    try:
                        t = float(parts[0])
                        pict_type = parts[1].strip().upper()
                        if pict_type == "I" and prev_type == "I" and timestamps:
                            timestamps.append(t)
                        prev_type = pict_type
                    except ValueError:
                        continue
            return timestamps
        except Exception:
            return []

    @staticmethod
    async def _extract_key_frames(video_path: str, scene_changes: List[float]) -> List[Dict[str, Any]]:
        key_frames = []
        timestamps = [0.0] + scene_changes[:5]
        for i, ts in enumerate(timestamps):
            key_frames.append({
                "frame_number": i,
                "timestamp": ts,
                "type": "scene_change" if ts > 0.0 else "start",
            })
        return key_frames

    @staticmethod
    async def _estimate_motion(video_path: str) -> List[Dict[str, Any]]:
        if not video_processing_service._check_ffprobe():
            return []
        return [{"timestamp": 0.0, "magnitude": 0.0, "direction": "none"}]

    @staticmethod
    async def _detect_targets_heuristic(media_info, video_path: str) -> Tuple[List[DetectedTarget], List[DetectedTarget]]:
        objects: List[DetectedTarget] = []
        faces: List[DetectedTarget] = []
        return objects, faces

    @staticmethod
    def _error_result(message: str) -> Dict[str, Any]:
        return {
            "analysis": VideoAnalysis(),
            "objects": [],
            "faces": [],
            "scenes": [],
            "motion": {},
            "ml_available": {},
            "error": message,
        }
