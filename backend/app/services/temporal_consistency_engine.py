from typing import Optional, List, Dict, Any
from app.schemas.phase9 import TemporalConsistencyReport
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class TemporalConsistencyEngine:
    @staticmethod
    async def analyze(video_path: str, frame_range: Optional[Dict[str, int]] = None) -> TemporalConsistencyReport:
        issues = []
        affected_frames = []
        severity = "low"

        try:
            media_info = await video_processing_service.inspect_media(video_path)
            duration = getattr(media_info, "duration_seconds", None)
            frame_count = getattr(media_info, "frame_count", None)
        except Exception as e:
            return TemporalConsistencyReport(
                score=0.0,
                issues=[f"Media inspection failed: {e}"],
                severity="critical",
                recommended_fix="Verify source file integrity.",
            )

        if frame_count is not None and frame_count <= 1:
            issues.append("Video has only one frame or frame count unavailable.")
            affected_frames.append(0)
            severity = "high"

        if duration is not None and duration < 0.5:
            issues.append("Video is extremely short; temporal consistency is not meaningful.")
            severity = "medium"

        scene_changes = await TemporalConsistencyEngine._detect_scene_changes(video_path)
        if len(scene_changes) > 10:
            issues.append(f"High scene change count detected ({len(scene_changes)}). Possible flicker or discontinuity.")
            affected_frames.extend([int(t * 30) for t in scene_changes])
            severity = "high"

        if not issues:
            score = 1.0
        elif severity == "critical":
            score = 0.0
        elif severity == "high":
            score = 0.4
        else:
            score = 0.7

        return TemporalConsistencyReport(
            score=score,
            issues=issues,
            affected_frames=affected_frames,
            severity=severity,
            recommended_fix="Retry generation with stronger temporal guidance or use a different provider." if issues else None,
            face_drift=severity in ("high", "critical"),
            identity_drift=severity in ("high", "critical"),
            lighting_jump=len(scene_changes) > 5,
            temporal_flicker=len(scene_changes) > 10,
        )

    @staticmethod
    async def _detect_scene_changes(video_path: str) -> List[float]:
        if not video_processing_service._check_ffprobe():
            return []
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_pts_time",
            "-of", "csv=p=0",
            video_path,
        ]
        try:
            import asyncio
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            timestamps = []
            for line in stdout.decode().strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        timestamps.append(float(line))
                    except ValueError:
                        continue
            return timestamps
        except Exception:
            return []
