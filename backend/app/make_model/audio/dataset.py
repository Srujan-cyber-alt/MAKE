"""
Audio dataset pipeline - legal-source validation, license metadata, split, provenance.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import hashlib
import json
from pathlib import Path
from datetime import datetime

from app.make_model.audio.architecture import AudioConfig
from app.make_model.audio.config_loader import load_audio_config


class AudioDatasetManager:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or load_audio_config("tiny")
        self._manifest: Dict[str, Any] = {
            "dataset_name": self.config.dataset.get("name", "audio-dataset"),
            "created_at": datetime.utcnow().isoformat(),
            "samples": [],
            "splits": {"train": [], "validation": [], "test": []},
            "licenses": [],
            "provenance": [],
        }

    async def initialize(self, config_path: Optional[str] = None) -> None:
        if config_path:
            self.config = load_audio_config(config_path)

    def validate_source(self, source_url: str, license_type: str) -> Dict[str, Any]:
        allowed_licenses = ["CC-BY", "CC-BY-SA", "MIT", "Apache-2.0", "public_domain"]
        if license_type not in allowed_licenses:
            return {"valid": False, "reason": f"License {license_type} not in allowed list"}
        return {"valid": True, "source_url": source_url, "license": license_type}

    def register_sample(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        path = Path(file_path)
        content_hash = self._hash_file(path)
        sample = {
            "file_path": str(path),
            "content_hash": content_hash,
            "metadata": metadata,
            "registered_at": datetime.utcnow().isoformat(),
        }
        self._manifest["samples"].append(sample)
        return sample

    def create_splits(self, ratios: Optional[Dict[str, float]] = None) -> Dict[str, List[str]]:
        ratios = ratios or self.config.dataset.get("split_ratios", {})
        samples = self._manifest["samples"]
        total = len(samples)
        if total == 0:
            return {"train": [], "validation": [], "test": []}
        train_end = int(total * ratios.get("train", 0.8))
        val_end = train_end + int(total * ratios.get("validation", 0.1))
        self._manifest["splits"] = {
            "train": [s["file_path"] for s in samples[:train_end]],
            "validation": [s["file_path"] for s in samples[train_end:val_end]],
            "test": [s["file_path"] for s in samples[val_end:]],
        }
        return self._manifest["splits"]

    def get_manifest(self) -> Dict[str, Any]:
        return dict(self._manifest)

    def save_manifest(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def _hash_file(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
