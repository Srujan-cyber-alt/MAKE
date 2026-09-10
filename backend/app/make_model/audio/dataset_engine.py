"""
Dataset Engine - autonomous legal local dataset ingestion for CPU training.

Supports local datasets with license/attribution tracking.
No network downloads - only local file scanning.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
import json
import hashlib
import os
import wave
import struct
from pathlib import Path
import numpy as np

from enum import Enum


from app.make_model.audio.manifest import LicenseType, DatasetManifest, DatasetEntry as ManifestEntry, DatasetEntry


@dataclass
class DatasetItem:
    path: str
    sha256: str
    duration: float
    sample_rate: int
    channels: int
    license: LicenseType
    attribution: str
    source: str
    language: str
    speaker_id: Optional[str]
    quality_score: float
    split: str
    file_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["license"] = self.license.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "DatasetItem":
        d["license"] = LicenseType(d["license"])
        return cls(**d)


    def ingest(self, dataset_id: str, name: str, file_paths: List[str], license_type: LicenseType) -> DatasetManifest:
        from app.make_model.audio.manifest import ALLOWED_LICENSES
        lic_val = license_type.value if hasattr(license_type, "value") else license_type
        if lic_val not in ALLOWED_LICENSES:
            raise ValueError(f"License {license_type} is not allowed for training")
        manifest = DatasetManifest(dataset_id=dataset_id, name=name, license=license_type)
        for fp in file_paths:
            sha = self.compute_sha256(fp)
            sr, channels, duration = self.get_wav_info(fp)
            entry = ManifestEntry(
                path=fp, size_bytes=0, content_hash=sha,
                format="wav", duration_seconds=duration,
                sample_rate=sr, channels=channels,
            )
            manifest.add_entry(entry)
        self._manifests[dataset_id] = manifest
        return manifest

    def get_manifest(self, dataset_id: str):
        return self._manifests.get(dataset_id)

    def verify_integrity(self, dataset_id: str) -> dict:
        manifest = self._manifests.get(dataset_id)
        if manifest is None:
            return {'status': 'not_found'}
        return manifest.verify_integrity()

    def check_license(self, dataset_id: str) -> dict:
        manifest = self._manifests.get(dataset_id)
        if manifest is None:
            return {'status': 'not_found'}
        return manifest.check_license()

    def list_datasets(self) -> List[str]:
        return list(self._manifests.keys())

@dataclass
class DatasetSplit:
    train: List[DatasetItem] = field(default_factory=list)
    validation: List[DatasetItem] = field(default_factory=list)
    test: List[DatasetItem] = field(default_factory=list)


class DatasetEngine:
    def __init__(self, dataset_dir: str, manifest_path: Optional[str] = None):
        self.dataset_dir = Path(dataset_dir)
        self.manifest_path = manifest_path or str(self.dataset_dir / "manifest.json")
        self.items: List[DatasetItem] = []
        self.splits = DatasetSplit()
        self._loaded = False
        self._manifacts: Dict[str, DatasetManifest] = {}
        self._manifests: Dict[str, DatasetManifest] = {}

    def ingest(self, dataset_id: str, name: str, file_paths: List[str], license_type: LicenseType) -> DatasetManifest:
        from app.make_model.audio.manifest import ALLOWED_LICENSES
        lic_val = license_type.value if hasattr(license_type, "value") else license_type
        if lic_val not in ALLOWED_LICENSES:
            raise ValueError(f"License {license_type} is not allowed for training")
        manifest = DatasetManifest(dataset_id=dataset_id, name=name, license=license_type)
        for fp in file_paths:
            sha = self.compute_sha256(fp)
            sr, channels, duration = self.get_wav_info(fp)
            entry = ManifestEntry(
                path=fp, size_bytes=0, content_hash=sha,
                format="wav", duration_seconds=duration,
                sample_rate=sr, channels=channels,
            )
            manifest.add_entry(entry)
        self._manifests[dataset_id] = manifest
        return manifest

    def get_manifest(self, dataset_id: str):
        return self._manifests.get(dataset_id)

    def verify_integrity(self, dataset_id: str) -> dict:
        manifest = self._manifests.get(dataset_id)
        if manifest is None:
            return {"status": "not_found"}
        return manifest.verify_integrity()

    def check_license(self, dataset_id: str) -> dict:
        manifest = self._manifests.get(dataset_id)
        if manifest is None:
            return {"status": "not_found"}
        return manifest.check_license()

    def list_datasets(self) -> List[str]:
        return list(self._manifests.keys())


    @staticmethod
    def compute_sha256(path: str, chunk_size: int = 65536) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def get_wav_info(path: str) -> tuple:
        try:
            with wave.open(path, "rb") as w:
                sr = w.getframerate()
                channels = w.getnchannels()
                frames = w.getnframes()
                duration = frames / sr if sr > 0 else 0.0
                return sr, channels, duration
        except Exception:
            return 0, 0, 0.0

    @staticmethod
    def compute_quality_score(path: str, sr: int, channels: int, duration: float) -> float:
        if sr < 16000 or channels == 0 or duration < 0.5 or duration > 600:
            return 0.0
        try:
            with wave.open(path, "rb") as w:
                n_frames = w.getnframes()
                sample_width = w.getsampwidth()
                if sample_width != 2:
                    return 0.5
                frames_data = w.readframes(n_frames)
                if len(frames_data) < n_frames * sample_width * channels:
                    return 0.3
                samples = np.frombuffer(frames_data, dtype=np.int16)
                if np.max(np.abs(samples)) > 32700:
                    return 0.4
                rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
                if rms < 50:
                    return 0.2
                return min(1.0, rms / 5000.0)
        except Exception:
            return 0.5

    def ingest_local(self, license_info: Dict[str, Any]) -> List[DatasetItem]:
        results: List[DatasetItem] = []
        if not self.dataset_dir.exists():
            return results
        seen_hashes: set = set()
        for wav_path in self.dataset_dir.rglob("*.wav"):
            sha = self.compute_sha256(str(wav_path))
            if sha in seen_hashes:
                continue
            seen_hashes.add(sha)
            sr, channels, duration = self.get_wav_info(str(wav_path))
            if sr == 0 or channels == 0:
                continue
            quality = self.compute_quality_score(str(wav_path), sr, channels, duration)
            if quality < 0.1:
                continue
            file_size = wav_path.stat().st_size
            speaker_id = license_info.get("speaker_id")
            lang = license_info.get("language", "en")
            item = DatasetItem(
                path=str(wav_path),
                sha256=sha,
                duration=duration,
                sample_rate=sr,
                channels=channels,
                license=LicenseType(license_info.get("license", "unknown")),
                attribution=license_info.get("attribution", ""),
                source=license_info.get("source", str(wav_path.parent.name)),
                language=lang,
                speaker_id=speaker_id,
                quality_score=quality,
                split="unassigned",
                file_size=file_size,
                metadata=license_info.get("metadata", {}),
            )
            results.append(item)
        self.items.extend(results)
        return results

    def assign_splits(self, train_ratio: float = 0.7, val_ratio: float = 0.15, test_ratio: float = 0.10, seed: int = 42) -> DatasetSplit:
        rng = np.random.RandomState(seed)
        items = sorted(self.items, key=lambda x: x.sha256)
        indices = rng.permutation(len(items))
        n = len(items)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        for i in indices[:train_end]:
            items[i].split = "train"
            self.splits.train.append(items[i])
        for i in indices[train_end:val_end]:
            items[i].split = "validation"
            self.splits.validation.append(items[i])
        for i in indices[val_end:]:
            items[i].split = "test"
            self.splits.test.append(items[i])
        return self.splits

    def normalize_audio(self, path: str, target_sr: int = 16000) -> Optional[np.ndarray]:
        sr, channels, duration = self.get_wav_info(path)
        if sr == 0:
            return None
        try:
            with wave.open(path, "rb") as w:
                n_frames = w.getnframes()
                frames_data = w.readframes(n_frames)
            samples = np.frombuffer(frames_data, dtype=np.int16).astype(np.float32)
            samples /= 32768.0
            if sr != target_sr:
                from scipy import signal as scipy_signal
                n = int(len(samples) * target_sr / sr)
                samples = scipy_signal.resample_poly(samples, 1, int(sr / target_sr))
            if np.max(np.abs(samples)) > 0:
                target_loudness = -23.0
                current_loudness = 10 * np.log10(np.mean(samples ** 2) + 1e-10)
                gain = 10 ** ((target_loudness - current_loudness) / 20)
                samples = np.clip(samples * gain, -0.99, 0.99)
            return samples.astype(np.float32)
        except Exception:
            return None

    def save_manifest(self) -> None:
        data = {
            "version": "1.0",
            "dataset_dir": str(self.dataset_dir),
            "total_items": len(self.items),
            "license_policy": "local_only_no_network_download",
            "train_count": len(self.splits.train),
            "validation_count": len(self.splits.validation),
            "test_count": len(self.splits.test),
            "items": [item.to_dict() for item in self.items],
        }
        Path(self.manifest_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_manifest(self) -> bool:
        try:
            with open(self.manifest_path, "r") as f:
                data = json.load(f)
            self.items = [DatasetItem.from_dict(item) for item in data["items"]]
            self.splits = DatasetSplit()
            for item in self.items:
                if item.split == "train":
                    self.splits.train.append(item)
                elif item.split == "validation":
                    self.splits.validation.append(item)
                elif item.split == "test":
                    self.splits.test.append(item)
            self._loaded = True
            return True
        except Exception:
            return False

    def get_training_batch(self, split: str = "train", batch_size: int = 8) -> List[DatasetItem]:
        target = self.splits.train if split == "train" else (self.splits.validation if split == "validation" else self.splits.test)
        if not target:
            return []
        rng = np.random.RandomState(42)
        indices = rng.choice(len(target), min(batch_size, len(target)), replace=False)
        return [target[i] for i in indices]

    def save_manifests(self, path: str) -> None:
        import json
        from pathlib import Path
        data = {
            did: m.to_dict() for did, m in self._manifests.items()
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_manifests(self, path: str) -> bool:
        import json
        from pathlib import Path
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for did, m_data in data.items():
                self._manifests[did] = DatasetManifest.from_dict(m_data)
            return True
        except Exception as e:
            return False
