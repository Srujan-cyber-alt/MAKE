"""MAKE Image Engine — Dataset Engine.

Legally usable image dataset acquisition with provenance tracking.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


@dataclass
class ImageDatasetConfig:
    sources: List[str] = field(default_factory=lambda: ["synthetic"])
    max_samples: int = 1000
    min_resolution: int = 256
    output_dir: str = "./dataset"
    dataset_version: str = "1.0.0"


class ImageDatasetEngine:
    def __init__(self, cfg: ImageDatasetConfig):
        self.cfg = cfg
        self.records: List[DatasetProvenance] = []

    def validate_license(self, source: str, license_name: str) -> bool:
        permitted = {"cc0", "cc-by", "cc-by-4.0", "public domain", "pixabay", "pexels", "coverr", "videvo"}
        forbidden = {"all rights reserved", "copyright", "cc-by-nc", "cc-by-nc-4.0", "cc-by-sa"}
        normalized = license_name.strip().lower()
        if normalized in forbidden:
            raise ValueError(f"License forbids training: {license_name}")
        if normalized == "unknown":
            raise ValueError("License is UNKNOWN")
        return normalized in permitted or normalized.startswith("cc-by")

    def add_sample(self, source: str, license_name: str, resolution: Tuple[int, int], quality: float, caption: str, data: bytes, split: str = "train") -> DatasetProvenance:
        self.validate_license(source, license_name)
        h = hashlib.sha256(data).hexdigest()
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


__all__ = [
    "DatasetProvenance",
    "ImageDatasetConfig",
    "ImageDatasetEngine",
]
