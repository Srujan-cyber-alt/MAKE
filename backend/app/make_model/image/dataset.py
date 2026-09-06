"""MAKE Image Engine — Dataset Engine.

Legally usable image dataset acquisition with provenance tracking.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class DatasetProvenance:
    source: str
    license: str
    rights: str
    resolution: Tuple[int, int]
    quality: float
    caption: str
    hash: str
    dataset_version: str
    split: str = "train"
    source_url: str = ""
    creator: str = ""
    acquired_at: str = ""
    permitted_use: str = "training"


@dataclass
class ImageDatasetConfig:
    sources: List[str] = field(default_factory=lambda: ["synthetic"])
    max_samples: int = 1000
    min_resolution: int = 256
    output_dir: str = "./dataset"
    dataset_version: str = "1.0.0"
    deduplicate: bool = True
    quality_threshold: float = 0.5


class ImageDatasetEngine:
    PERMITTED_LICENSES = {
        "cc0", "cc-by", "cc-by-4.0", "public domain", "pixabay", "pexels", "coverr", "videvo"
    }
    FORBIDDEN_LICENSES = {
        "all rights reserved", "copyright", "cc-by-nc", "cc-by-nc-4.0", "cc-by-sa"
    }

    def __init__(self, cfg: ImageDatasetConfig):
        self.cfg = cfg
        self.records: List[DatasetProvenance] = []
        self.hashes: set = set()

    def validate_license(self, source: str, license_name: str) -> bool:
        normalized = license_name.strip().lower()
        if normalized in self.FORBIDDEN_LICENSES:
            raise ValueError(f"License forbids training: {license_name}")
        if normalized == "unknown":
            raise ValueError("License is UNKNOWN")
        return normalized in self.PERMITTED_LICENSES or normalized.startswith("cc-by")

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _is_duplicate(self, data: bytes) -> bool:
        if not self.cfg.deduplicate:
            return False
        h = self._compute_hash(data)
        if h in self.hashes:
            return True
        self.hashes.add(h)
        return False

    def _assess_quality(self, data: bytes) -> float:
        try:
            img = np.frombuffer(data, dtype=np.uint8)
            return min(1.0, len(img) / 10000.0)
        except Exception:
            return 0.0

    def add_sample(self, source: str, license_name: str, resolution: Tuple[int, int], quality: float, caption: str, data: bytes, split: str = "train", source_url: str = "", creator: str = "", acquired_at: str = "", permitted_use: str = "training") -> DatasetProvenance:
        self.validate_license(source, license_name)
        if self._is_duplicate(data):
            raise ValueError("Duplicate sample rejected")
        if resolution[0] < self.cfg.min_resolution or resolution[1] < self.cfg.min_resolution:
            raise ValueError(f"Resolution {resolution} below minimum {self.cfg.min_resolution}")
        if quality < self.cfg.quality_threshold:
            raise ValueError(f"Quality {quality} below threshold {self.cfg.quality_threshold}")
        h = self._compute_hash(data)
        record = DatasetProvenance(
            source=source,
            license=license_name,
            rights="training permitted",
            resolution=resolution,
            quality=quality,
            caption=caption,
            hash=h,
            dataset_version=self.cfg.dataset_version,
            split=split,
            source_url=source_url,
            creator=creator,
            acquired_at=acquired_at or __import__('datetime').datetime.utcnow().isoformat() + "Z",
            permitted_use=permitted_use,
        )
        self.records.append(record)
        return record

    def build_manifest(self) -> Dict[str, Any]:
        return {
            "version": self.cfg.dataset_version,
            "total_samples": len(self.records),
            "sources": {},
            "licenses": {},
            "samples": [r.__dict__ for r in self.records],
        }

    def save_manifest(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.build_manifest(), f, indent=2)

    def save_samples(self) -> None:
        os.makedirs(self.cfg.output_dir, exist_ok=True)
        for i, record in enumerate(self.records):
            pass

    def split_dataset(self, train_ratio: float = 0.8, val_ratio: float = 0.1) -> Dict[str, List[int]]:
        n = len(self.records)
        indices = list(range(n))
        np.random.shuffle(indices)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        return {
            "train": indices[:train_end],
            "validation": indices[train_end:val_end],
            "test": indices[val_end:],
        }


__all__ = [
    "DatasetProvenance",
    "ImageDatasetConfig",
    "ImageDatasetEngine",
]
