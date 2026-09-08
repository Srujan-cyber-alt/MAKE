"""Artifact Manager — tracks all output artifacts with full provenance.

Every output is traceable to:
    job ID, model/version, input, configuration, execution state, timestamp,
    provenance.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, delete

from app.intelligence.config import intelligence_settings
from app.intelligence.schemas import ArtifactRecord
from app.intelligence.models import ArtifactRecordOrm


class ArtifactManager:
    """Manages artifact records and their provenance metadata."""

    def __init__(self) -> None:
        self._artifact_dir = intelligence_settings.artifact_dir

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    @staticmethod
    def compute_digest(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def register_artifact(
        self,
        job_id: str,
        type: str,
        path: str,
        content_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        model_version: Optional[str] = None,
        input_digest: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        execution_state: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRecord:
        """Register an output artifact with full provenance."""
        configuration = configuration or {}
        execution_state = execution_state or {}
        provenance = provenance or {}

        provenance.setdefault("job_id", job_id)
        provenance.setdefault("registered_at", datetime.utcnow().isoformat())
        if model_version:
            provenance.setdefault("model_version", model_version)
        if input_digest:
            provenance.setdefault("input_digest", input_digest)

        async with self._session()() as session:
            orm = ArtifactRecordOrm(
                job_id=job_id,
                type=type,
                path=path,
                content_type=content_type,
                size_bytes=size_bytes,
                model_version=model_version,
                input_digest=input_digest,
                configuration=configuration,
                execution_state=execution_state,
                timestamp=datetime.utcnow(),
                provenance=provenance,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)

        # Also write a provenance sidecar file
        self._write_provenance_sidecar(job_id, orm.id, provenance, configuration, execution_state)

        return ArtifactRecord(
            artifact_id=orm.id,
            job_id=orm.job_id,
            type=orm.type,
            path=orm.path,
            content_type=orm.content_type,
            size_bytes=orm.size_bytes,
            model_version=orm.model_version,
            input_digest=orm.input_digest,
            configuration=orm.configuration,
            execution_state=orm.execution_state,
            timestamp=orm.timestamp,
            provenance=orm.provenance,
        )

    def _write_provenance_sidecar(
        self,
        job_id: str,
        artifact_id: str,
        provenance: Dict[str, Any],
        configuration: Dict[str, Any],
        execution_state: Dict[str, Any],
    ) -> None:
        d = os.path.join(self._artifact_dir, job_id)
        os.makedirs(d, exist_ok=True)
        sidecar_path = os.path.join(d, f"{artifact_id}.provenance.json")
        try:
            with open(sidecar_path, "w") as f:
                json.dump(
                    {
                        "provenance": provenance,
                        "configuration": configuration,
                        "execution_state": execution_state,
                        "written_at": datetime.utcnow().isoformat(),
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception:
            pass

    async def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        async with self._session()() as session:
            orm = await session.get(ArtifactRecordOrm, artifact_id)
            if orm is None:
                return None
        return self._to_record(orm)

    async def get_artifacts_for_job(self, job_id: str) -> List[ArtifactRecord]:
        async with self._session()() as session:
            result = await session.execute(
                select(ArtifactRecordOrm)
                .where(ArtifactRecordOrm.job_id == job_id)
                .order_by(ArtifactRecordOrm.timestamp.desc())
            )
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def get_artifact_provenance(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get full provenance chain for an artifact."""
        async with self._session()() as session:
            orm = await session.get(ArtifactRecordOrm, artifact_id)
            if orm is None:
                return None

        provenance_chain: List[Dict[str, Any]] = []
        current: Optional[ArtifactRecordOrm] = orm

        # Follow provenance chain through job
        job_id = orm.job_id
        # Add related artifacts from the same job
        async with self._session()() as session:
            result = await session.execute(
                select(ArtifactRecordOrm)
                .where(ArtifactRecordOrm.job_id == job_id)
            )
            related = result.scalars().all()

        for r in related:
            provenance_chain.append({
                "artifact_id": r.id,
                "type": r.type,
                "path": r.path,
                "model_version": r.model_version,
                "input_digest": r.input_digest,
                "timestamp": r.timestamp.isoformat(),
                "provenance": r.provenance,
            })

        return {
            "artifact_id": orm.id,
            "job_id": orm.job_id,
            "chain": provenance_chain,
        }

    async def clear_all(self) -> int:
        async with self._session()() as session:
            result = await session.execute(delete(ArtifactRecordOrm))
            await session.commit()
            return result.rowcount

    @staticmethod
    def _to_record(orm: ArtifactRecordOrm) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=orm.id,
            job_id=orm.job_id,
            type=orm.type,
            path=orm.path,
            content_type=orm.content_type,
            size_bytes=orm.size_bytes,
            model_version=orm.model_version,
            input_digest=orm.input_digest,
            configuration=orm.configuration,
            execution_state=orm.execution_state,
            timestamp=orm.timestamp,
            provenance=orm.provenance,
        )
