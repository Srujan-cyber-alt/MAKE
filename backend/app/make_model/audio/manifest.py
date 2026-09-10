"""
Dataset manifest: metadata for dataset ingestion.

Describes a dataset's entries, license, provenance, and integrity hashes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LicenseType(str, Enum):
    CC0 = "CC0"
    CC_BY = "CC-BY"
    CC_BY_SA = "CC-BY-SA"
    CC_BY_NC = "CC-BY-NC"
    CC_BY_ND = "CC-BY-ND"
    MIT = "MIT"
    APACHE_2 = "Apache-2.0"
    BSD_3 = "BSD-3"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


ALLOWED_LICENSES = {lt.value for lt in LicenseType if lt != LicenseType.UNKNOWN}


@dataclass
class DatasetEntry:
    """A single file entry within a dataset manifest."""

    path: str
    size_bytes: int = 0
    content_hash: str = ""
    format: str = "wav"
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "format": self.format,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetEntry":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class DatasetManifest:
    """Manifest describing a dataset's provenance and integrity."""

    dataset_id: str
    name: str
    license: LicenseType = LicenseType.UNKNOWN
    entries: List[DatasetEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    description: str = ""
    source_url: str = ""
    version: str = "1.0"
    num_entries: int = 0
    total_size_bytes: int = 0
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.num_entries:
            self.num_entries = len(self.entries)
        if not self.total_size_bytes:
            self.total_size_bytes = sum(e.size_bytes for e in self.entries)

    def add_entry(self, entry: DatasetEntry) -> None:
        self.entries.append(entry)
        self.num_entries = len(self.entries)
        self.total_size_bytes += entry.size_bytes
        self.updated_at = time.time()

    def remove_entry(self, path: str) -> bool:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.path != path]
        if len(self.entries) != before:
            self.num_entries = len(self.entries)
            self.total_size_bytes = sum(e.size_bytes for e in self.entries)
            self.updated_at = time.time()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "license": self.license.value if isinstance(self.license, LicenseType) else self.license,
            "entries": [e.to_dict() for e in self.entries],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description,
            "source_url": self.source_url,
            "version": self.version,
            "num_entries": self.num_entries,
            "total_size_bytes": self.total_size_bytes,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetManifest":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "license" in filtered and not isinstance(filtered["license"], LicenseType):
            filtered["license"] = LicenseType(filtered["license"])
        filtered["entries"] = [DatasetEntry.from_dict(e) for e in filtered.get("entries", [])]
        return cls(**filtered)
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify SHA-256 hashes of all entries."""
        import hashlib
        results = []
        all_ok = True
        for entry in self.entries:
            try:
                h = hashlib.sha256()
                with open(entry.path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                actual_hash = h.hexdigest()
                ok = actual_hash == entry.content_hash
                results.append({"path": entry.path, "ok": ok})
                if not ok:
                    all_ok = False
            except Exception as e:
                results.append({"path": entry.path, "ok": False, "error": str(e)})
                all_ok = False
        return {"status": "ok" if all_ok else "error", "entries": results}

    def check_license(self) -> Dict[str, Any]:
        """Check if the dataset license allows training."""
        from app.make_model.audio.manifest import ALLOWED_LICENSES
        license_val = self.license.value if isinstance(self.license, LicenseType) else self.license
        allowed = license_val in ALLOWED_LICENSES
        return {"license": license_val, "allowed": allowed, "status": "ok" if allowed else "not_allowed"}
