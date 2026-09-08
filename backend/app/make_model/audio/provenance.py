"""
Audio provenance tracking - immutable records of generation lineage.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime

from app.make_model.audio.types import ProvenanceRecord


class AudioProvenanceTracker:
    def __init__(self, storage_path: str = "/tmp/audio_provenance.json") -> None:
        self.storage_path = Path(storage_path)
        self._records: List[ProvenanceRecord] = []
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            self._records = [ProvenanceRecord(**r) for r in data]

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.__dict__ for r in self._records]
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def record(
        self,
        artifact_id: str,
        model_id: str,
        model_version: str,
        generation_parameters: Dict[str, Any],
        source_inputs: List[str],
        transformations: List[Dict[str, Any]],
        content_hash: str,
        dataset_lineage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceRecord:
        record = ProvenanceRecord(
            artifact_id=artifact_id,
            model_id=model_id,
            model_version=model_version,
            generation_parameters=generation_parameters,
            source_inputs=source_inputs,
            transformations=transformations,
            timestamps=[datetime.utcnow().isoformat()],
            content_hash=content_hash,
            dataset_lineage=dataset_lineage,
            metadata=metadata or {},
        )
        self._records.append(record)
        self._save()
        return record

    def get_record(self, artifact_id: str) -> Optional[ProvenanceRecord]:
        for record in self._records:
            if record.artifact_id == artifact_id:
                return record
        return None

    def get_history(self, model_id: Optional[str] = None) -> List[ProvenanceRecord]:
        if model_id:
            return [r for r in self._records if r.model_id == model_id]
        return list(self._records)

    def verify_hash(self, artifact_id: str, file_path: str) -> bool:
        record = self.get_record(artifact_id)
        if not record:
            return False
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest() == record.content_hash
