#!/usr/bin/env python3
"""MAKE Image Engine — Dataset Downloader.

Downloads legally usable images for training.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


def download_sample(url: str, timeout: int = 30) -> Optional[bytes]:
    import requests
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def validate_image(data: bytes, min_resolution: int = 256) -> Optional[Tuple[int, int]]:
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode != "RGB":
            img = img.convert("RGB")
        if img.width < min_resolution or img.height < min_resolution:
            return None
        return (img.width, img.height)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="MAKE Image Dataset Downloader")
    parser.add_argument("--output-dir", type=str, default="./dataset", help="Output directory")
    parser.add_argument("--max-samples", type=int, default=50, help="Maximum samples to download")
    parser.add_argument("--min-resolution", type=int, default=256, help="Minimum image resolution")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    sources = [
        ("https://picsum.photos/seed/{}/512/512", "picsum", "picsum license"),
        ("https://picsum.photos/seed/{}/256/256", "picsum", "picsum license"),
    ]

    from app.make_model.image.dataset import ImageDatasetConfig, ImageDatasetEngine

    cfg = ImageDatasetConfig(
        sources=["picsum"],
        max_samples=args.max_samples,
        min_resolution=args.min_resolution,
        output_dir=args.output_dir,
    )
    engine = ImageDatasetEngine(cfg)

    downloaded = 0
    seeds = list(range(1000, 1000 + args.max_samples * 2))
    for seed in seeds:
        if downloaded >= args.max_samples:
            break
        for url_template, source, license_name in sources:
            url = url_template.format(seed)
            print(f"[Dataset] Downloading {url}")
            data = download_sample(url)
            if data is None:
                continue
            resolution = validate_image(data, args.min_resolution)
            if resolution is None:
                continue
            try:
                record = engine.add_sample(
                    source=source,
                    license_name=license_name,
                    resolution=resolution,
                    quality=0.8,
                    caption=f"sample_{seed}",
                    data=data,
                    split="train",
                    source_url=url,
                    creator="unknown",
                    permitted_use="training",
                )
                img_path = os.path.join(args.output_dir, f"{record.hash}.png")
                with open(img_path, "wb") as f:
                    f.write(data)
                downloaded += 1
                print(f"[Dataset] Saved {img_path} ({resolution})")
            except ValueError as e:
                print(f"[Dataset] Skipped: {e}")
            time.sleep(0.1)

    manifest_path = os.path.join(args.output_dir, "manifest.json")
    engine.save_manifest(manifest_path)
    print(f"[Dataset] Manifest saved to {manifest_path}")
    print(f"[Dataset] Total samples: {downloaded}")


if __name__ == "__main__":
    main()
