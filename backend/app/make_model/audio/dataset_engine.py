"""
Dataset engine for legal dataset ingestion.

Handles manifest creation, license validation, and SHA-256 integrity
verification of audio datasets.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.manifest import DatasetManifest, DatasetEntry, LicenseType, ALLOWED_LICENSES


class DatasetEngine:
    """Legal dataset ingestion with manifest, license, and SHA-256 tracking."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else Path("/tmp/dataset_engine.json")
        self.manifests: Dict[str, DatasetManifest] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return
        for raw in data.get("manifests", []):
            manifest = DatasetManifest.from_dict(raw)
            self.manifests[manifest.dataset_id] = manifest

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"manifests": [m.to_dict() for m in self.manifests.values()]}
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(self.storage_path)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest(self, dataset_id: str, name: str, files: List[str], license_type: LicenseType, **kwargs: Any) -> DatasetManifest:
        if license_type.value not in ALLOWED_LICENSES:
            raise ValueError(f"Unsupported license: {license_type}")
        entries: List[DatasetEntry] = []
        for path in files:
            file_path = Path(path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            content_hash = self._sha256_file(file_path)
            entries.append(DatasetEntry(
                path=str(file_path),
                size_bytes=file_path.stat().st_size,
                content_hash=content_hash,
            ))
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            name=name,
            license=license_type,
            entries=entries,
            created_at=time.time(),
            **{k: v for k, v in kwargs.items() if k in DatasetManifest.__dataclass_fields__},
        )
        self.manifests[dataset_id] = manifest
        self._save()
        return manifest

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_manifest(self, dataset_id: str) -> Optional[DatasetManifest]:
        return self.manifests.get(dataset_id)

    def list_datasets(self) -> List[str]:
        return list(self.manifests.keys())

    def verify_integrity(self, dataset_id: str) -> Dict[str, Any]:
        manifest = self.manifests.get(dataset_id)
        if manifest is None:
            return {"status": "not_found"}
        results: List[Dict[str, Any]] = []
        ok = True
        for entry in manifest.entries:
            path = Path(entry.path)
            if not path.exists():
                results.append({"path": entry.path, "status": "missing"})
                ok = False
                continue
            actual = self._sha256_file(path)
            match = actual == entry.content_hash
            results.append({"path": entry.path, "status": "ok" if match else "mismatch"})
            if not match:
                ok = False
        return {"status": "ok" if ok else "failed", "dataset_id": dataset_id, "entries": results}

    def check_license(self, dataset_id: str) -> Dict[str, Any]:
        manifest = self.manifests.get(dataset_id)
        if manifest is None:
            return {"status": "not_found"}
        return {
            "dataset_id": dataset_id,
            "license": manifest.license.value,
            "allowed": manifest.license.value in ALLOWED_LICENSES,
        }