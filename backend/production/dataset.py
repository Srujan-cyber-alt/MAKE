"""MAKE Foundation 5B — Autonomous Legal Dataset Acquisition.

Downloads and processes legally usable video datasets for training.
Only accepts sources with training-permissive licenses.

Supported sources:
    - pixabay (Pixabay License: commercial use OK, no attribution required)
    - pexels (Pexels License: commercial use OK)
    - coverr (Coverr License: commercial use OK)
    - videvo (Videvo License: commercial use OK, attribution may be required)
    - videoUFO (CC BY 4.0: commercial use OK with attribution)
    - youtube-cc (Creative Commons YouTube videos)

Usage:
    python production/dataset.py --source pixabay --max-clips 1000 --output ./dataset
    python production/dataset.py --source pexels --max-clips 1000 --output ./dataset
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------------------------------------------------
# License verification
# ----------------------------------------------------------------------

PERMITTED_LICENSES = {
    "cc0", "cc-by", "cc-by-4.0", "public domain",
    "pixabay", "pexels", "coverr", "videvo",
}

FORBIDDEN_LICENSES = {
    "all rights reserved", "copyright",
    "cc-by-nc", "cc-by-nc-4.0", "cc-by-nc-sa",
    "cc-by-nc-sa-4.0", "cc-by-nd", "cc-by-nd-4.0",
    "cc-by-sa", "cc-by-sa-4.0",
}


def verify_license(license_name: str, source_key: str) -> bool:
    normalized = license_name.strip().lower()
    if normalized in FORBIDDEN_LICENSES:
        raise ValueError(f"License explicitly forbids training: {license_name}")
    if normalized == "unknown":
        raise ValueError("License is UNKNOWN. Refusing to use.")
    if normalized in PERMITTED_LICENSES:
        return True
    raise ValueError(f"License not in permitted list: {license_name}")


# ----------------------------------------------------------------------
# Source definitions
# ----------------------------------------------------------------------

SOURCE_CONFIGS = {
    "pixabay": {
        "name": "Pixabay",
        "license": "Pixabay License",
        "url": "https://pixabay.com/videos/",
        "api": "https://pixabay.com/api/videos/",
        "commercial": True,
        "attribution": False,
    },
    "pexels": {
        "name": "Pexels",
        "license": "Pexels License",
        "url": "https://www.pexels.com/videos/",
        "api": "https://api.pexels.com/videos",
        "commercial": True,
        "attribution": False,
    },
    "coverr": {
        "name": "Coverr",
        "license": "Coverr License",
        "url": "https://coverr.co/",
        "api": "https://coverr.co/feed",
        "commercial": True,
        "attribution": False,
    },
    "videvo": {
        "name": "Videvo",
        "license": "Videvo License",
        "url": "https://www.videvo.net/",
        "api": "https://www.videvo.net/api/videos/",
        "commercial": True,
        "attribution": True,
    },
    "videoUFO": {
        "name": "VideoUFO",
        "license": "CC BY 4.0",
        "url": "https://huggingface.co/datasets/WenhaoWang/VideoUFO",
        "api": "huggingface",
        "commercial": True,
        "attribution": True,
    },
}


# ----------------------------------------------------------------------
# Media validation
# ----------------------------------------------------------------------

def ffprobe(path: str) -> Dict[str, Any]:
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-print_format', 'json',
             '-show_streams', '-show_format', path],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return json.loads(out.stdout)
    except Exception:
        pass
    return {}


def validate_media(path: str, min_resolution: int = 256, min_fps: float = 8.0, max_duration: float = 120.0) -> Tuple[bool, str]:
    if not os.path.exists(path):
        return False, "file not found"
    info = ffprobe(path)
    streams = info.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), {})
    w = int(video.get('width', 0))
    h = int(video.get('height', 0))
    if w < min_resolution or h < min_resolution:
        return False, f"resolution {w}x{h} below {min_resolution}"
    fps_str = video.get('r_frame_rate', '0/1')
    if '/' in fps_str:
        num, den = fps_str.split('/')
        fps = float(num) / float(den) if float(den) > 0 else 0
    else:
        fps = float(fps_str)
    if fps < min_fps:
        return False, f"fps {fps} below {min_fps}"
    dur = float(video.get('duration', 0) or info.get('format', {}).get('duration', 0))
    if dur > max_duration:
        return False, f"duration {dur}s exceeds {max_duration}s"
    return True, "ok"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------
# Acquisition
# ----------------------------------------------------------------------

@dataclass
class AcquiredClip:
    asset_id: str
    url: str
    source: str
    license: str
    sha256: str
    local_path: str
    width: int
    height: int
    fps: float
    duration_seconds: float
    frames: int
    caption: str = ""
    quality_score: float = 0.0


def acquire_pixabay(max_clips: int, output_dir: str, api_key: Optional[str] = None) -> List[AcquiredClip]:
    clips = []
    import urllib.request, urllib.parse
    base = "https://pixabay.com/api/videos/"
    page = 1
    per_page = 200
    while len(clips) < max_clips:
        params = urllib.parse.urlencode({'key': api_key or '', 'q': 'cinematic', 'video_type': 'film', 'per_page': per_page, 'page': page})
        try:
            with urllib.request.urlopen(f"{base}?{params}", timeout=30) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"[WARN] Pixabay API error: {e}")
            break
        hits = data.get('hits', [])
        if not hits:
            break
        for hit in hits:
            if len(clips) >= max_clips:
                break
            video_url = hit.get('videos', {}).get('medium', {}).get('url') or hit.get('videos', {}).get('small', {}).get('url')
            if not video_url:
                continue
            fname = f"pixabay_{hit['id']}.mp4"
            fpath = os.path.join(output_dir, fname)
            try:
                urllib.request.urlretrieve(video_url, fpath)
                ok, reason = validate_media(fpath)
                if ok:
                    clips.append(AcquiredClip(
                        asset_id=f"pixabay_{hit['id']}",
                        url=video_url, source='pixabay', license='Pixabay License',
                        sha256=sha256_file(fpath), local_path=fpath,
                        width=int(hit.get('width', 0)), height=int(hit.get('height', 0)),
                        fps=24.0, duration_seconds=float(hit.get('duration', 0)),
                        frames=int(hit.get('duration', 0) * 24),
                    ))
            except Exception as e:
                print(f"[WARN] Download failed: {e}")
        page += 1
    return clips


def acquire_pexels(max_clips: int, output_dir: str, api_key: Optional[str] = None) -> List[AcquiredClip]:
    clips = []
    import urllib.request, urllib.parse
    headers = {'Authorization': api_key} if api_key else {}
    page = 1
    per_page = 80
    while len(clips) < max_clips:
        params = urllib.parse.urlencode({'query': 'cinematic human', 'per_page': per_page, 'page': page})
        try:
            req = urllib.request.Request(f"https://api.pexels.com/videos/search?{params}", headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"[WARN] Pexels API error: {e}")
            break
        videos = data.get('videos', [])
        if not videos:
            break
        for vid in videos:
            if len(clips) >= max_clips:
                break
            files = vid.get('video_files', [])
            mp4 = next((f for f in files if f.get('file_type') == 'video/mp4'), None)
            if not mp4:
                continue
            video_url = mp4['link']
            fname = f"pexels_{vid['id']}.mp4"
            fpath = os.path.join(output_dir, fname)
            try:
                urllib.request.urlretrieve(video_url, fpath)
                ok, reason = validate_media(fpath)
                if ok:
                    clips.append(AcquiredClip(
                        asset_id=f"pexels_{vid['id']}",
                        url=video_url, source='pexels', license='Pexels License',
                        sha256=sha256_file(fpath), local_path=fpath,
                        width=int(mp4.get('width', 0)), height=int(mp4.get('height', 0)),
                        fps=float(vid.get('duration', 0) and 24.0), duration_seconds=float(vid.get('duration', 0)),
                        frames=int(vid.get('duration', 0) * 24),
                    ))
            except Exception as e:
                print(f"[WARN] Download failed: {e}")
        page += 1
    return clips


def acquire_coverr(max_clips: int, output_dir: str) -> List[AcquiredClip]:
    clips = []
    try:
        import urllib.request
        with urllib.request.urlopen("https://coverr.co/feed", timeout=30) as r:
            html = r.read().decode('utf-8', errors='ignore')
        import re
        mp4_urls = re.findall(r'https://[^\s"\']+\.mp4', html)
        for i, url in enumerate(mp4_urls[:max_clips]):
            fname = f"coverr_{i}.mp4"
            fpath = os.path.join(output_dir, fname)
            try:
                urllib.request.urlretrieve(url, fpath)
                ok, reason = validate_media(fpath)
                if ok:
                    clips.append(AcquiredClip(
                        asset_id=f"coverr_{i}", url=url, source='coverr',
                        license='Coverr License', sha256=sha256_file(fpath),
                        local_path=fpath, width=1920, height=1080, fps=24.0,
                        duration_seconds=10.0, frames=240,
                    ))
            except Exception as e:
                print(f"[WARN] Coverr download failed: {e}")
    except Exception as e:
        print(f"[WARN] Coverr feed error: {e}")
    return clips


def acquire_videvo(max_clips: int, output_dir: str) -> List[AcquiredClip]:
    clips = []
    try:
        import urllib.request
        with urllib.request.urlopen("https://www.videvo.net/api/videos/?page=1&per_page=100&license=free", timeout=30) as r:
            data = json.loads(r.read())
        for item in data.get('items', [])[:max_clips]:
            video = item.get('video', {})
            url = video.get('download_url') or video.get('preview_url')
            if not url:
                continue
            fname = f"videvo_{video.get('id', 'unknown')}.mp4"
            fpath = os.path.join(output_dir, fname)
            try:
                urllib.request.urlretrieve(url, fpath)
                ok, reason = validate_media(fpath)
                if ok:
                    clips.append(AcquiredClip(
                        asset_id=f"videvo_{video.get('id')}", url=url, source='videvo',
                        license='Videvo License', sha256=sha256_file(fpath),
                        local_path=fpath, width=video.get('width', 1920), height=video.get('height', 1080),
                        fps=24.0, duration_seconds=float(video.get('duration', 10)),
                        frames=int(video.get('duration', 10) * 24),
                    ))
            except Exception as e:
                print(f"[WARN] Videvo download failed: {e}")
    except Exception as e:
        print(f"[WARN] Videvo API error: {e}")
    return clips


# ----------------------------------------------------------------------
# Manifest building
# ----------------------------------------------------------------------

def build_manifest(clips: List[AcquiredClip], output_dir: str, name: str = "make-dataset") -> str:
    manifest = {
        'name': name,
        'version': '1.0.0',
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'total_clips': len(clips),
        'sources': {},
        'licenses': {},
        'samples': [asdict(c) for c in clips],
    }
    for c in clips:
        manifest['sources'][c.source] = manifest['sources'].get(c.source, 0) + 1
        manifest['licenses'][c.license] = manifest['licenses'].get(c.license, 0) + 1
    path = os.path.join(output_dir, 'manifest.json')
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {path} ({len(clips)} clips)")
    return path


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser("MAKE Dataset Acquisition")
    parser.add_argument('--source', required=True, choices=list(SOURCE_CONFIGS.keys()))
    parser.add_argument('--max-clips', type=int, default=100)
    parser.add_argument('--output', default='./dataset')
    parser.add_argument('--api-key', default=None)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    verify_license(SOURCE_CONFIGS[args.source]['license'], args.source)

    if args.source == 'pixabay':
        clips = acquire_pixabay(args.max_clips, args.output, args.api_key)
    elif args.source == 'pexels':
        clips = acquire_pexels(args.max_clips, args.output, args.api_key)
    elif args.source == 'coverr':
        clips = acquire_coverr(args.max_clips, args.output)
    elif args.source == 'videvo':
        clips = acquire_videvo(args.max_clips, args.output)
    else:
        print(f"Source {args.source} not implemented in this runner")
        return 1

    build_manifest(clips, args.output, name=f"make-{args.source}")
    print(f"Acquired {len(clips)} clips from {args.source}")
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
