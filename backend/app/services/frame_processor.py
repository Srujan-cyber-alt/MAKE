import asyncio
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from app.schemas.phase7 import FrameExtractionResult
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class FrameProcessor:
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir or "/tmp") / "makeai-frames"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def extract_frames(
        self,
        asset_id: str,
        project_id: str,
        user_id: str,
        frame_range: Optional[Dict[str, int]] = None,
        interval: Optional[float] = None,
        output_format: str = "png",
        max_frames: int = 100,
    ) -> FrameExtractionResult:
        source_path = await self._resolve_source(asset_id, project_id, user_id)
        if not source_path or not Path(source_path).exists():
            raise FileNotFoundError(f"Source asset not found for frame extraction: {asset_id}")

        output_dir = self.temp_dir / f"frames_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            if interval is not None:
                return await self._extract_by_interval(source_path, output_dir, interval, output_format, max_frames)
            elif frame_range:
                return await self._extract_by_range(source_path, output_dir, frame_range, output_format, max_frames)
            else:
                return await self._extract_key_frames(source_path, output_dir, output_format, max_frames)
        finally:
            pass

    async def _extract_by_interval(
        self,
        source_path: str,
        output_dir: Path,
        interval: float,
        output_format: str,
        max_frames: int,
    ) -> FrameExtractionResult:
        if not video_processing_service._check_ffmpeg():
            raise RuntimeError("ffmpeg not available for frame extraction")
        frame_paths = []
        timestamps = []
        pattern = str(output_dir / f"frame_%04d.{output_format}")
        cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-vf", f"fps=1/{interval}",
            "-q:v", "2" if output_format == "jpg" else "1",
            pattern,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            frame_paths = sorted([str(p) for p in output_dir.glob(f"*.{output_format}")])
            if len(frame_paths) > max_frames:
                frame_paths = frame_paths[:max_frames]
            for i, p in enumerate(frame_paths):
                timestamps.append(i * interval)
            media_info = await video_processing_service.inspect_media(source_path)
            return FrameExtractionResult(
                frame_paths=frame_paths,
                timestamps=timestamps,
                count=len(frame_paths),
                resolution=(getattr(media_info, "width", None), getattr(media_info, "height", None)) if media_info else None,
                format=output_format,
            )
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return FrameExtractionResult(frame_paths=[], timestamps=[], count=0)

    async def _extract_by_range(
        self,
        source_path: str,
        output_dir: Path,
        frame_range: Dict[str, int],
        output_format: str,
        max_frames: int,
    ) -> FrameExtractionResult:
        start = frame_range.get("start", 0)
        end = frame_range.get("end", 0)
        if start == end:
            return FrameExtractionResult(frame_paths=[], timestamps=[], count=0)
        frame_count = min(end - start, max_frames)
        pattern = str(output_dir / f"frame_%04d.{output_format}")
        cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-vf", f"select='between(n\\,{start}\\,{end})',setpts=N/FRAME_RATE/TB",
            "-vsync", "vfr",
            "-q:v", "2" if output_format == "jpg" else "1",
            pattern,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            frame_paths = sorted([str(p) for p in output_dir.glob(f"*.{output_format}")])[:frame_count]
            timestamps = [start + i for i in range(len(frame_paths))]
            media_info = await video_processing_service.inspect_media(source_path)
            return FrameExtractionResult(
                frame_paths=frame_paths,
                timestamps=timestamps,
                count=len(frame_paths),
                resolution=(getattr(media_info, "width", None), getattr(media_info, "height", None)) if media_info else None,
                format=output_format,
            )
        except Exception as e:
            logger.error(f"Frame range extraction failed: {e}")
            return FrameExtractionResult(frame_paths=[], timestamps=[], count=0)

    async def _extract_key_frames(
        self,
        source_path: str,
        output_dir: Path,
        output_format: str,
        max_frames: int,
    ) -> FrameExtractionResult:
        pattern = str(output_dir / f"frame_%04d.{output_format}")
        cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-vf", "select='eq(pict_type,I)'",
            "-vsync", "vfr",
            "-q:v", "2" if output_format == "jpg" else "1",
            "-frames:v", str(max_frames),
            pattern,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            frame_paths = sorted([str(p) for p in output_dir.glob(f"*.{output_format}")])[:max_frames]
            timestamps = list(range(len(frame_paths)))
            media_info = await video_processing_service.inspect_media(source_path)
            return FrameExtractionResult(
                frame_paths=frame_paths,
                timestamps=timestamps,
                count=len(frame_paths),
                resolution=(getattr(media_info, "width", None), getattr(media_info, "height", None)) if media_info else None,
                format=output_format,
            )
        except Exception as e:
            logger.error(f"Key frame extraction failed: {e}")
            return FrameExtractionResult(frame_paths=[], timestamps=[], count=0)

    async def reconstruct_video(
        self,
        frame_paths: List[str],
        output_path: str,
        fps: float = 30.0,
        audio_path: Optional[str] = None,
    ) -> str:
        if not frame_paths:
            raise ValueError("No frame paths provided for reconstruction")
        if not video_processing_service._check_ffmpeg():
            raise RuntimeError("ffmpeg not available for video reconstruction")
        list_file = self.temp_dir / f"frames_{uuid.uuid4().hex}.txt"
        with open(list_file, "w") as f:
            for p in frame_paths:
                f.write(f"file '{p}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
        ]
        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", audio_path, "-c:a", "aac", "-shortest"])
        else:
            cmd.extend(["-an"])
        cmd.append(output_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=300)
            if proc.returncode != 0:
                raise RuntimeError("FFmpeg reconstruction failed")
            if not Path(output_path).exists():
                raise RuntimeError("Reconstructed video file is missing")
            return output_path
        finally:
            list_file.unlink(missing_ok=True)

    async def apply_per_frame_operation(
        self,
        frame_paths: List[str],
        operation: callable,
        output_dir: Optional[str] = None,
    ) -> List[str]:
        output_dir = Path(output_dir or self.temp_dir) / f"operated_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)
        result_paths = []
        for i, frame_path in enumerate(frame_paths):
            try:
                out_path = str(output_dir / f"operated_{i:04d}.png")
                await operation(frame_path, out_path)
                result_paths.append(out_path)
            except Exception as e:
                logger.error(f"Per-frame operation failed on frame {i}: {e}")
                result_paths.append(frame_path)
        return result_paths

    async def cleanup_frames(self, frame_paths: List[str]):
        for p in frame_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass

    async def _resolve_source(self, asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None


frame_processor = FrameProcessor()
