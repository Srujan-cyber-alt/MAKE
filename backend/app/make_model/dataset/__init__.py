"""
MAKE dataset preparation for the proprietary model program.

Pipeline:
  1. Read a directory of source videos + optional sidecar captions.
  2. Decode each to a fixed-length, fixed-resolution MP4 clip (FFmpeg).
  3. Write a DatasetManifest with provenance (SHA-256, ffprobe shape).
  4. Optional validation: missing fields, dimensions, duplicates, captions.

Inputs and outputs are real files. No downloads. No fabricated content.
"""

from __future__ import annotations
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.utils import (
    paths, ensure_dirs, dump_json, load_json, now_iso, sha256_file,
    get_logger, human_size,
)


logger = get_logger("make_model.dataset")

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


@dataclass
class DatasetConfig:
    name: str = "make-dataset-v0"
    input_dir: str = ""
    output_dir: str = ""
    target_short_side: int = 64
    target_frames: int = 8
    target_fps: int = 8
    min_bytes: int = 1024
    max_clips: int = 0
    include_globs: List[str] = field(default_factory=lambda: ["*.mp4", "*.mov", "*.webm", "*.mkv", "*.avi"])
    require_caption: bool = False
    seed: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetConfig":
        return cls(**d)


@dataclass
class ClipEntry:
    id: str
    source_path: str
    source_sha256: str
    clip_path: str
    clip_sha256: str
    clip_bytes: int
    width: int
    height: int
    frames: int
    fps: float
    duration_seconds: float
    caption: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ffprobe_json(path: str) -> Dict[str, Any]:
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return {}
        return json.loads(r.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def _read_caption(video_path: Path) -> str:
    for ext in (".txt", ".caption", ".json"):
        sidecar = video_path.with_suffix(ext)
        if sidecar.exists():
            try:
                return sidecar.read_text(encoding="utf-8").strip()
            except Exception:
                continue
    return ""


def _video_stream_info(path: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    info = _ffprobe_json(path)
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return (s.get("width"), s.get("height"), _safe_float(s.get("avg_frame_rate")))
    return (None, None, None)


def _safe_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if isinstance(s, str) and "/" in s:
        try:
            num, den = s.split("/")
            num = float(num)
            den = float(den)
            if den == 0:
                return None
            return num / den
        except ValueError:
            return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _decode_clip(src: str, dst: str, target_short_side: int, target_frames: int, target_fps: int) -> bool:
    try:
        vf = (
            f"scale='if(gt(iw,ih),{target_short_side},-2)':'if(gt(ih,iw),{target_short_side},-2)'"
        )
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", src,
            "-vf", vf,
            "-frames:v", str(target_frames),
            "-r", str(target_fps),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-an", "-movflags", "+faststart",
            dst,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"ffmpeg failed for {src}: {e}")
        return False


def prepare_dataset(cfg: DatasetConfig) -> Dict[str, Any]:
    if not cfg.input_dir:
        raise ValueError("DatasetConfig.input_dir is required")
    in_dir = Path(cfg.input_dir).expanduser().resolve()
    if not in_dir.exists() or not in_dir.is_dir():
        raise FileNotFoundError(f"Dataset input dir not found: {in_dir}")
    out_dir = (
        Path(cfg.output_dir).expanduser().resolve()
        if cfg.output_dir
        else ensure_dirs()["datasets"] / cfg.name
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = out_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    candidates: List[Path] = []
    for pat in cfg.include_globs:
        candidates.extend(sorted(in_dir.glob(pat)))
    candidates = [c for c in candidates if c.is_file() and c.stat().st_size >= cfg.min_bytes]
    if not candidates:
        raise RuntimeError(
            f"No usable video files in {in_dir}. "
            f"Globs: {cfg.include_globs}, min size {cfg.min_bytes} bytes."
        )
    if cfg.max_clips > 0:
        candidates = candidates[: cfg.max_clips]

    entries: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for i, src in enumerate(candidates):
        caption = _read_caption(src)
        if cfg.require_caption and not caption:
            skipped.append({"path": str(src), "reason": "no caption sidecar"})
            continue
        w0, h0, _ = _video_stream_info(str(src))
        if not w0:
            skipped.append({"path": str(src), "reason": "no video stream"})
            continue
        clip_id = f"{i:06d}-{src.stem[:40]}"
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", clip_id)
        dst = clips_dir / f"{safe}.mp4"
        ok = _decode_clip(str(src), str(dst), cfg.target_short_side, cfg.target_frames, cfg.target_fps)
        if not ok:
            skipped.append({"path": str(src), "reason": "ffmpeg decode failed"})
            continue
        w, h, fps = _video_stream_info(str(dst))
        try:
            clip_bytes = dst.stat().st_size
            clip_sha = sha256_file(str(dst))
            src_sha = sha256_file(str(src))
        except OSError as e:
            skipped.append({"path": str(src), "reason": f"stat/hash error: {e}"})
            continue
        info = _ffprobe_json(str(dst))
        dur = _safe_float(info.get("format", {}).get("duration")) or float(cfg.target_frames) / max(cfg.target_fps, 1)
        entry = ClipEntry(
            id=clip_id,
            source_path=str(src),
            source_sha256=src_sha,
            clip_path=str(dst),
            clip_sha256=clip_sha,
            clip_bytes=clip_bytes,
            width=int(w or 0),
            height=int(h or 0),
            frames=int(cfg.target_frames),
            fps=float(fps or cfg.target_fps),
            duration_seconds=float(dur),
            caption=caption,
            created_at=now_iso(),
        )
        entries.append(entry.to_dict())
        if (i + 1) % 10 == 0:
            logger.info(f"Prepared {i+1}/{len(candidates)} clips")

    if not entries:
        raise RuntimeError(
            f"All {len(candidates)} candidate files were skipped. "
            f"Reasons sample: {skipped[:5]}. Check inputs and FFmpeg."
        )

    manifest = {
        "name": cfg.name,
        "description": cfg.description,
        "config": cfg.to_dict(),
        "created_at": now_iso(),
        "clip_count": len(entries),
        "skipped": skipped,
        "total_bytes": sum(e["clip_bytes"] for e in entries),
        "clips": entries,
    }
    out_path = out_dir / "manifest.json"
    dump_json(out_path, manifest)
    logger.info(
        f"Dataset '{cfg.name}' built: {len(entries)} clips, "
        f"{human_size(manifest['total_bytes'])}, manifest at {out_path}"
    )
    return {
        "manifest_path": str(out_path),
        "clip_count": len(entries),
        "skipped_count": len(skipped),
        "total_bytes": manifest["total_bytes"],
    }


def load_manifest(path: str | Path) -> Dict[str, Any]:
    return load_json(path)


def iter_clips(manifest: Dict[str, Any]):
    for c in manifest.get("clips", []):
        yield c, c.get("caption", "")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class DatasetIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    sample_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_dataset(manifest: Dict[str, Any], require_caption: bool = False) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    seen_hashes: Dict[str, str] = {}
    for clip in manifest.get("clips", []):
        sid = clip.get("id", "?")
        for field in ("clip_path", "clip_sha256", "width", "height", "frames", "fps", "duration_seconds"):
            if not clip.get(field):
                issues.append(DatasetIssue("error", "MISSING_FIELD", f"clip {sid} missing {field}", sid).to_dict())
        w, h = clip.get("width", 0), clip.get("height", 0)
        if w and h and (w % 2 or h % 2):
            issues.append(DatasetIssue("warning", "ODD_DIMENSION", f"clip {sid} has odd dimensions {w}x{h}", sid).to_dict())
        if (w and w < 16) or (h and h < 16):
            issues.append(DatasetIssue("error", "DIMENSION_TOO_SMALL", f"clip {sid} {w}x{h} < 16", sid).to_dict())
        if clip.get("fps", 0) <= 0:
            issues.append(DatasetIssue("error", "INVALID_FPS", f"clip {sid} has fps={clip.get('fps')}", sid).to_dict())
        if clip.get("duration_seconds", 0) <= 0:
            issues.append(DatasetIssue("error", "INVALID_DURATION", f"clip {sid} has non-positive duration", sid).to_dict())
        h_ = clip.get("clip_sha256")
        if h_:
            if h_ in seen_hashes:
                issues.append(DatasetIssue("error", "DUPLICATE_HASH",
                    f"clip {sid} has same hash as {seen_hashes[h_]}", sid).to_dict())
            else:
                seen_hashes[h_] = sid
        cp = clip.get("clip_path")
        if cp and not os.path.exists(cp):
            issues.append(DatasetIssue("error", "FILE_MISSING", f"clip {sid} file missing on disk: {cp}", sid).to_dict())
        if cp and os.path.exists(cp):
            actual = os.path.getsize(cp)
            if clip.get("clip_bytes") and actual != clip["clip_bytes"]:
                issues.append(DatasetIssue("error", "SIZE_MISMATCH",
                    f"clip {sid} size {actual} != manifest {clip['clip_bytes']}", sid).to_dict())
        if require_caption and not clip.get("caption"):
            issues.append(DatasetIssue("error", "MISSING_CAPTION", f"clip {sid} has no caption", sid).to_dict())
    return {
        "manifest_name": manifest.get("name"),
        "clip_count": manifest.get("clip_count"),
        "issue_count": len(issues),
        "error_count": sum(1 for i in issues if i["severity"] == "error"),
        "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        "issues": issues,
    }
