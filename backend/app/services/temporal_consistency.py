from typing import List, Dict, Any, Optional
from app.services.video_processing import video_processing_service


class TemporalConsistencyValidator:

    @staticmethod
    async def validate(video_path: str, frame_range: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        media_info = await video_processing_service.inspect_media(video_path)
        issues = []
        scores = []

        frame_count = getattr(media_info, "frame_count", None)
        duration = getattr(media_info, "duration_seconds", None)

        if frame_count is not None and frame_count <= 1:
            issues.append("Video has only one frame or frame count unavailable.")
            scores.append(0.0)

        if duration is not None and duration < 0.5:
            issues.append("Video is extremely short; temporal consistency is not meaningful.")
            scores.append(0.0)

        scene_changes = await TemporalConsistencyValidator._detect_scene_changes(video_path)
        if len(scene_changes) > 10:
            issues.append(f"High scene change count detected ({len(scene_changes)}). Possible flicker or discontinuity.")
            scores.append(0.5)
        else:
            scores.append(0.9)

        consistency_score = max(0.0, min(1.0, sum(scores) / max(len(scores), 1)))

        return {
            "valid": len(issues) == 0,
            "consistency_score": consistency_score,
            "issues": issues,
            "scene_changes": scene_changes,
            "frame_count": frame_count,
            "duration_seconds": duration,
        }

    @staticmethod
    async def _detect_scene_changes(video_path: str) -> List[float]:
        if not video_processing_service._check_ffprobe():
            return []

        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_pts_time",
            "-of", "csv=p=0",
            video_path,
        ]

        try:
            import asyncio
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
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
