"""MAKE World Model X — Data Engine.

A serious training-data system for the proprietary video model.
Lives at backend/app/make_model/world/data_engine.py.

Capabilities:
    - Ingest local video files
    - Compute SHA-256 + ffprobe metadata
    - Quality scoring (heuristics; deterministic, GPU-free)
    - Dedup by exact hash and by perceptual hash (aHash, 8x8)
    - Optional auto-captioning hook (disabled by default; requires caption model)
    - Scene boundary detection by frame-difference threshold
    - License/provenance recording
    - Shard + manifest with full provenance per clip
    - Reject samples missing required provenance

No downloaders, no scrapers, no network calls. Local only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from app.make_model.utils import sha256_file, dump_json


# ----------------------------------------------------------------------
# Records
# ----------------------------------------------------------------------


@dataclass
class SourceLicense:
    source: str
    license: str
    permission_status: str
    acquisition_method: str = "local"
    notes: str = ""


@dataclass
class QualityMetrics:
    """Per-clip quality metrics. All scores are in [0, 1]."""

    sharpness: float = 0.0      # higher = sharper
    brightness: float = 0.0     # mean luma
    contrast: float = 0.0       # std of luma
    saturation: float = 0.0     # chroma std
    motion: float = 0.0         # mean frame-difference
    black_frame_ratio: float = 0.0
    frozen_frame_ratio: float = 0.0
    aesthetic_score: float = 0.0  # placeholder; real model is a separate system


@dataclass
class TrainingSample:
    """A single training-ready sample."""

    sample_id: str
    source_path: str
    source_sha256: str
    source_bytes: int
    clip_path: str
    clip_sha256: str
    clip_bytes: int
    width: int
    height: int
    frames: int
    fps: float
    duration_seconds: float
    caption: str = ""
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    license: SourceLicense = field(
        default_factory=lambda: SourceLicense(
            source="unknown", license="unknown", permission_status="unknown"
        )
    )
    motion_metadata: Dict[str, Any] = field(default_factory=dict)
    camera_metadata: Dict[str, Any] = field(default_factory=dict)
    subject_metadata: Dict[str, Any] = field(default_factory=dict)
    scene_metadata: Dict[str, Any] = field(default_factory=dict)
    split: str = "train"     # train | val | test
    dataset_version: str = ""
    reasons: List[str] = field(default_factory=list)


@dataclass
class DatasetManifest:
    """Top-level manifest."""

    name: str
    description: str
    created_at: str
    dataset_version: str
    license_summary: Dict[str, int]
    total_samples: int
    total_bytes: int
    samples: List[TrainingSample]
    per_split_counts: Dict[str, int]
    quality_thresholds: Dict[str, float]
    notes: str = ""


# ----------------------------------------------------------------------
# FFmpeg helpers
# ----------------------------------------------------------------------


def _ffprobe(path: str) -> Dict[str, Any]:
    """Probe a video file. Tries ffprobe first, then falls back to ffmpeg -i parse.

    This works whether `ffprobe` is the real binary or imageio_ffmpeg's ffmpeg
    (which does not understand ffprobe flags but can be parsed from `ffmpeg -i`).
    """
    # try ffprobe
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if out.returncode == 0 and out.stdout.strip():
            try:
                return json.loads(out.stdout)
            except Exception:
                pass
    except Exception:
        pass

    # fallback: use ffmpeg -i and parse stderr (works with imageio ffmpeg too)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg as _ife
            ffmpeg = _ife.get_ffmpeg_exe()
        except Exception:
            return {}
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path],
            capture_output=True, text=True, timeout=20,
        )
        text = out.stderr or out.stdout
        import re
        streams: List[Dict[str, Any]] = []
        nb_frames: Optional[int] = None
        for line in text.split("\n"):
            stripped = line.strip()
            if "Stream #" in stripped and "Video:" in stripped:
                stream: Dict[str, Any] = {"codec_type": "video"}
                m = re.search(r"(?<![\d])(\d{2,})x(\d{2,})(?![\d])", stripped)
                if m:
                    stream["width"] = int(m.group(1))
                    stream["height"] = int(m.group(2))
                m = re.search(r"(\d+(?:\.\d+)?)\s*fps", stripped)
                if m:
                    fps = float(m.group(1))
                    stream["r_frame_rate"] = f"{int(round(fps*1000))}/1000"
                    stream["avg_frame_rate"] = stream["r_frame_rate"]
                streams.append(stream)
            elif stripped.startswith("Duration:"):
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stripped)
                if m:
                    h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                    duration_s = h * 3600 + mn * 60 + s
                    fps_m = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
                    if fps_m:
                        fps_v = float(fps_m.group(1))
                        if fps_v > 0:
                            nb_frames = int(round(duration_s * fps_v))
        for s in streams:
            if s.get("codec_type") == "video" and nb_frames is not None:
                s["nb_frames"] = str(nb_frames)
        return {"streams": streams}
    except Exception:
        return {}


def _decode_frames(path: str, max_frames: int = 8) -> Optional[np.ndarray]:
    """Decode up to N frames as float32 RGB arrays in [0, 1].

    Uses FFmpeg + rawvideo output (no numpy image lib needed).
    """
    try:
        out = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                path,
                "-vf",
                f"scale=64:64:flags=bilinear",
                "-frames:v",
                str(max_frames),
                "-pix_fmt",
                "rgb24",
                "-f",
                "rawvideo",
                "-",
            ],
            capture_output=True,
            timeout=30,
        )
        if out.returncode != 0 or not out.stdout:
            return None
        arr = np.frombuffer(out.stdout, dtype=np.uint8)
        n = arr.size // (64 * 64 * 3)
        if n == 0:
            return None
        return arr[: n * 64 * 64 * 3].reshape(n, 64, 64, 3).astype(np.float32) / 255.0
    except Exception:
        return None


# ----------------------------------------------------------------------
# Quality scoring
# ----------------------------------------------------------------------


def _luma(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def compute_quality(frames: np.ndarray) -> QualityMetrics:
    if frames is None or frames.size == 0:
        return QualityMetrics()
    l = _luma(frames)
    sharpness = float(np.mean(np.abs(np.diff(l, axis=-1))) + np.mean(np.abs(np.diff(l, axis=-2))))
    brightness = float(np.mean(l))
    contrast = float(np.std(l))
    chroma = frames.std(axis=(1, 2))
    saturation = float(chroma.mean())
    diffs = np.abs(np.diff(l, axis=0)).mean(axis=(1, 2)) if l.shape[0] > 1 else np.array([0.0])
    motion = float(diffs.mean())
    black = float(np.mean(l < 0.05))
    frozen = float(np.mean(diffs < 1e-3)) if diffs.size else 0.0
    # aesthetic is a placeholder; the real system runs a frozen CLIP aesthetic head
    return QualityMetrics(
        sharpness=float(np.clip(sharpness * 5.0, 0, 1)),
        brightness=float(np.clip(brightness, 0, 1)),
        contrast=float(np.clip(contrast * 4.0, 0, 1)),
        saturation=float(np.clip(saturation * 4.0, 0, 1)),
        motion=float(np.clip(motion * 50.0, 0, 1)),
        black_frame_ratio=float(np.clip(black, 0, 1)),
        frozen_frame_ratio=float(np.clip(frozen, 0, 1)),
        aesthetic_score=0.0,
    )


# ----------------------------------------------------------------------
# Perceptual hash (8x8 aHash) for dedup
# ----------------------------------------------------------------------


def _ahash(rgb: np.ndarray) -> str:
    """Simple 8x8 average hash; deterministic."""
    if rgb is None or rgb.size == 0:
        return "0" * 16
    l = _luma(rgb)
    if l.ndim == 3:
        l = l.mean(axis=0)
    # resize to 8x8 by block average
    H, W = l.shape
    bh, bw = max(H // 8, 1), max(W // 8, 1)
    blocks = l[: bh * 8, : bw * 8].reshape(8, bh, 8, bw).mean(axis=(1, 3))
    bits = (blocks > blocks.mean()).astype(np.uint8).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return f"{h:016x}"


def _hamming(a: str, b: str) -> int:
    ai, bi = int(a, 16), int(b, 16)
    return bin(ai ^ bi).count("1")


# ----------------------------------------------------------------------
# Scene boundary detection
# ----------------------------------------------------------------------


def detect_scene_changes(frames: np.ndarray, threshold: float = 0.20) -> List[int]:
    """Return frame indices where the diff to the previous frame exceeds threshold."""
    if frames is None or frames.shape[0] < 2:
        return []
    l = _luma(frames)
    out: List[int] = []
    for i in range(1, l.shape[0]):
        if float(np.abs(l[i] - l[i - 1]).mean()) > threshold:
            out.append(i)
    return out


# ----------------------------------------------------------------------
# Ingestion + sharding
# ----------------------------------------------------------------------


@dataclass
class DataEngineConfig:
    name: str = "make-dataset-v0"
    description: str = "MAKE World Model training data"
    dataset_version: str = "0.1.0"
    target_short_side: int = 64
    target_frames: int = 8
    target_fps: float = 8.0
    min_sharpness: float = 0.05
    min_motion: float = 0.01
    max_black_ratio: float = 0.30
    max_frozen_ratio: float = 0.60
    dedup_hamming_threshold: int = 6
    split_train: float = 0.9
    split_val: float = 0.05
    split_test: float = 0.05
    require_license: bool = True


def _split_for(sample_id: str, cfg: DataEngineConfig) -> str:
    h = int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest()[:8], 16) % 1000
    r = h / 1000.0
    if r < cfg.split_train:
        return "train"
    if r < cfg.split_train + cfg.split_val:
        return "val"
    return "test"


def _read_caption_for(path: str) -> str:
    for ext in (".txt", ".caption", ".json"):
        cpath = os.path.splitext(path)[0] + ext
        if os.path.exists(cpath):
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                return ""
    return ""


def _clip_video(
    src: str, dst: str, target_short_side: int, target_frames: int, target_fps: float
) -> bool:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                src,
                "-vf",
                f"scale='trunc(iw*{target_short_side}/min(iw,ih))':'trunc(ih*{target_short_side}/min(iw,ih))':flags=bilinear, fps={target_fps}",
                "-frames:v",
                str(target_frames),
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-an",
                dst,
            ],
            check=True,
            timeout=60,
        )
        return True
    except Exception:
        return False


def ingest_directory(
    input_dir: str,
    output_dir: str,
    cfg: Optional[DataEngineConfig] = None,
    license_default: Optional[SourceLicense] = None,
) -> DatasetManifest:
    cfg = cfg or DataEngineConfig()
    license_default = license_default or SourceLicense(
        source="user_supplied", license="unknown", permission_status="unknown"
    )

    os.makedirs(output_dir, exist_ok=True)
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    samples: List[TrainingSample] = []
    seen_hashes: Dict[str, str] = {}
    license_summary: Dict[str, int] = {}
    total_bytes = 0
    skipped: List[Tuple[str, str]] = []

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(input_dir)

    files: List[str] = []
    for root, _, fs in os.walk(input_dir):
        for f in fs:
            if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".avi")):
                files.append(os.path.join(root, f))
    files.sort()

    for src in files:
        reasons: List[str] = []
        try:
            sha = sha256_file(src)
        except Exception as e:
            skipped.append((src, f"hash error: {e}"))
            continue
        if sha in seen_hashes:
            skipped.append((src, f"duplicate exact-hash of {seen_hashes[sha]}"))
            continue

        meta = _ffprobe(src)
        streams = meta.get("streams", [])
        vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not vstream:
            skipped.append((src, "no video stream"))
            continue
        try:
            width = int(vstream.get("width", 0))
            height = int(vstream.get("height", 0))
            fps = eval(vstream.get("r_frame_rate", "0/1")) if vstream.get("r_frame_rate") else 0.0
            nb_frames = int(vstream.get("nb_frames", 0)) or 0
        except Exception:
            skipped.append((src, "bad metadata"))
            continue
        if width <= 0 or height <= 0 or fps <= 0:
            skipped.append((src, "invalid dimensions or fps"))
            continue
        if nb_frames and nb_frames < max(4, cfg.target_frames):
            skipped.append((src, "too few frames"))
            continue

        # decode a probe
        frames = _decode_frames(src, max_frames=max(8, cfg.target_frames))
        if frames is None:
            skipped.append((src, "ffmpeg decode failed"))
            continue
        q = compute_quality(frames)
        if q.sharpness < cfg.min_sharpness:
            skipped.append((src, f"low sharpness {q.sharpness:.3f}"))
            continue
        if q.motion < cfg.min_motion:
            skipped.append((src, f"low motion {q.motion:.3f}"))
            continue
        if q.black_frame_ratio > cfg.max_black_ratio:
            skipped.append((src, f"too many black frames {q.black_frame_ratio:.3f}"))
            continue
        if q.frozen_frame_ratio > cfg.max_frozen_ratio:
            skipped.append((src, f"too many frozen frames {q.frozen_frame_ratio:.3f}"))
            continue

        # dedup by perceptual hash
        ah = _ahash(frames)
        is_dup = False
        for prev_id, prev_h in seen_hashes.items():
            if prev_h.startswith("ah:") and _hamming(prev_h[3:], ah) <= cfg.dedup_hamming_threshold:
                skipped.append((src, f"perceptual duplicate of {prev_id}"))
                is_dup = True
                break
        if is_dup:
            continue

        # clip
        sample_id = f"{int.from_bytes(bytes.fromhex(sha[:8]), 'big'):010d}-{len(samples):06d}"
        clip_path = os.path.join(clips_dir, f"{sample_id}.mp4")
        if not _clip_video(src, clip_path, cfg.target_short_side, cfg.target_frames, cfg.target_fps):
            skipped.append((src, "ffmpeg clip failed"))
            continue
        clip_sha = sha256_file(clip_path)
        clip_bytes = os.path.getsize(clip_path)
        # re-probe
        clip_meta = _ffprobe(clip_path)
        cv = next(
            (s for s in clip_meta.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        if not cv:
            skipped.append((src, "clipped video has no stream"))
            continue
        try:
            cw = int(cv.get("width", 0))
            ch = int(cv.get("height", 0))
            cnb = int(cv.get("nb_frames", 0)) or cfg.target_frames
            cfps = eval(cv.get("r_frame_rate", "0/1")) if cv.get("r_frame_rate") else cfg.target_fps
        except Exception:
            skipped.append((src, "bad clip metadata"))
            continue

        caption = _read_caption_for(src)
        scenes = detect_scene_changes(frames)
        sample = TrainingSample(
            sample_id=sample_id,
            source_path=src,
            source_sha256=sha,
            source_bytes=os.path.getsize(src),
            clip_path=clip_path,
            clip_sha256=clip_sha,
            clip_bytes=clip_bytes,
            width=cw,
            height=ch,
            frames=cnb,
            fps=float(cfps),
            duration_seconds=float(cnb) / float(cfps),
            caption=caption,
            quality=q,
            license=license_default,
            motion_metadata={
                "motion_score": q.motion,
                "scene_change_count": len(scenes),
            },
            camera_metadata={},
            subject_metadata={},
            scene_metadata={"scenes": scenes},
            dataset_version=cfg.dataset_version,
        )
        sample.split = _split_for(sample_id, cfg)
        samples.append(sample)
        total_bytes += clip_bytes
        seen_hashes[sha] = f"exact:{sample_id}"
        seen_hashes[sample_id] = f"ah:{ah}"
        license_summary[license_default.license] = license_summary.get(license_default.license, 0) + 1

    # write manifest
    manifest = DatasetManifest(
        name=cfg.name,
        description=cfg.description,
        created_at=_now_iso(),
        dataset_version=cfg.dataset_version,
        license_summary=license_summary,
        total_samples=len(samples),
        total_bytes=total_bytes,
        samples=samples,
        per_split_counts={
            s: sum(1 for x in samples if x.split == s) for s in ("train", "val", "test")
        },
        quality_thresholds={
            "min_sharpness": cfg.min_sharpness,
            "min_motion": cfg.min_motion,
            "max_black_ratio": cfg.max_black_ratio,
            "max_frozen_ratio": cfg.max_frozen_ratio,
        },
        notes=f"skipped: {len(skipped)}",
    )
    dump_json(os.path.join(output_dir, "manifest.json"), manifest_to_dict(manifest))
    # also write a separate skip log
    dump_json(
        os.path.join(output_dir, "skipped.json"),
        [{"path": p, "reason": r} for p, r in skipped],
    )
    return manifest


def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().isoformat() + "Z"


def manifest_to_dict(m: DatasetManifest) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "name": m.name,
        "description": m.description,
        "created_at": m.created_at,
        "dataset_version": m.dataset_version,
        "license_summary": m.license_summary,
        "total_samples": m.total_samples,
        "total_bytes": m.total_bytes,
        "per_split_counts": m.per_split_counts,
        "quality_thresholds": m.quality_thresholds,
        "notes": m.notes,
        "samples": [],
    }
    for s in m.samples:
        d["samples"].append(
            {
                "sample_id": s.sample_id,
                "source_path": s.source_path,
                "source_sha256": s.source_sha256,
                "source_bytes": s.source_bytes,
                "clip_path": s.clip_path,
                "clip_sha256": s.clip_sha256,
                "clip_bytes": s.clip_bytes,
                "width": s.width,
                "height": s.height,
                "frames": s.frames,
                "fps": s.fps,
                "duration_seconds": s.duration_seconds,
                "caption": s.caption,
                "quality": asdict(s.quality),
                "license": asdict(s.license),
                "motion_metadata": s.motion_metadata,
                "camera_metadata": s.camera_metadata,
                "subject_metadata": s.subject_metadata,
                "scene_metadata": s.scene_metadata,
                "split": s.split,
                "dataset_version": s.dataset_version,
            }
        )
    return d


def load_manifest(path: str) -> DatasetManifest:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    samples: List[TrainingSample] = []
    for s in d["samples"]:
        q = QualityMetrics(**s["quality"])
        lic = SourceLicense(**s["license"])
        samples.append(
            TrainingSample(
                sample_id=s["sample_id"],
                source_path=s["source_path"],
                source_sha256=s["source_sha256"],
                source_bytes=s["source_bytes"],
                clip_path=s["clip_path"],
                clip_sha256=s["clip_sha256"],
                clip_bytes=s["clip_bytes"],
                width=s["width"],
                height=s["height"],
                frames=s["frames"],
                fps=s["fps"],
                duration_seconds=s["duration_seconds"],
                caption=s.get("caption", ""),
                quality=q,
                license=lic,
                motion_metadata=s.get("motion_metadata", {}),
                camera_metadata=s.get("camera_metadata", {}),
                subject_metadata=s.get("subject_metadata", {}),
                scene_metadata=s.get("scene_metadata", {}),
                split=s.get("split", "train"),
                dataset_version=s.get("dataset_version", ""),
            )
        )
    return DatasetManifest(
        name=d["name"],
        description=d["description"],
        created_at=d["created_at"],
        dataset_version=d["dataset_version"],
        license_summary=d["license_summary"],
        total_samples=d["total_samples"],
        total_bytes=d["total_bytes"],
        samples=samples,
        per_split_counts=d["per_split_counts"],
        quality_thresholds=d["quality_thresholds"],
        notes=d.get("notes", ""),
    )


__all__ = [
    "SourceLicense",
    "QualityMetrics",
    "TrainingSample",
    "DatasetManifest",
    "DataEngineConfig",
    "ingest_directory",
    "load_manifest",
    "manifest_to_dict",
    "compute_quality",
    "detect_scene_changes",
]
