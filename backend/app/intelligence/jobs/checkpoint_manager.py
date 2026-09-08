"""Checkpoint Manager — persists resumable state for jobs.

Checkpoints are written to both the database (for crash recovery) and
optionally to JSON files (for out-of-band inspection).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete

from app.intelligence.config import intelligence_settings
from app.intelligence.schemas import CheckpointSpec
from app.intelligence.models import JobCheckpointOrm


class CheckpointManager:
    """Manages job checkpoints with dual persistence (DB + file)."""

    def __init__(self) -> None:
        self._checkpoint_dir = intelligence_settings.checkpoint_dir

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    def _file_path(self, job_id: str, checkpoint_id: str) -> str:
        d = os.path.join(self._checkpoint_dir, job_id)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{checkpoint_id}.json")

    async def create_checkpoint(
        self,
        job_id: str,
        step_id: str,
        state: Dict[str, Any],
        progress: float = 0.0,
        completed_steps: Optional[List[str]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Create and persist a checkpoint for a job."""
        completed_steps = completed_steps or []
        cp_id = f"ckpt-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        async with self._session()() as session:
            orm = JobCheckpointOrm(
                job_id=job_id,
                step_id=step_id,
                state=state,
                progress=progress,
                completed_steps=completed_steps,
                notes=notes,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            cp_data = {
                "id": orm.id,
                "job_id": orm.job_id,
                "step_id": orm.step_id,
                "state": orm.state,
                "progress": orm.progress,
                "completed_steps": orm.completed_steps or [],
                "notes": orm.notes,
                "file_path": orm.file_path,
                "created_at": orm.created_at.isoformat(),
            }

        # Write to file as well
        file_path = self._file_path(job_id, orm.id)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            payload = {
                "id": orm.id,
                "job_id": orm.job_id,
                "step_id": orm.step_id,
                "state": state,
                "progress": progress,
                "completed_steps": completed_steps,
                "notes": notes,
                "created_at": orm.created_at.isoformat(),
            }
            with open(file_path, "w") as f:
                json.dump(payload, f, indent=2, default=str)
        except Exception:
            pass

        return cp_data

    async def load_latest_checkpoint(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load the most recent checkpoint for a job."""
        async with self._session()() as session:
            result = await session.execute(
                select(JobCheckpointOrm)
                .where(JobCheckpointOrm.job_id == job_id)
                .order_by(JobCheckpointOrm.created_at.desc())
                .limit(1)
            )
            orm = result.scalar_one_or_none()

        if orm is None:
            return None

        cp_data = {
            "id": orm.id,
            "job_id": orm.job_id,
            "step_id": orm.step_id,
            "state": orm.state,
            "progress": orm.progress,
            "completed_steps": orm.completed_steps or [],
            "notes": orm.notes,
            "file_path": orm.file_path,
            "created_at": orm.created_at.isoformat(),
        }

        # Also try to read from file for verification
        file_path = self._file_path(job_id, orm.id)
        if os.path.exists(file_path):
            try:
                with open(file_path) as f:
                    file_data = json.load(f)
                # Prefer DB as source of truth, but verify consistency
                cp_data["file_exists"] = True
                cp_data["file_data_consistent"] = file_data.get("id") == orm.id
            except Exception:
                cp_data["file_exists"] = False
                cp_data["file_data_consistent"] = False

        return cp_data

    async def list_checkpoints(self, job_id: str) -> List[Dict[str, Any]]:
        async with self._session()() as session:
            result = await session.execute(
                select(JobCheckpointOrm)
                .where(JobCheckpointOrm.job_id == job_id)
                .order_by(JobCheckpointOrm.created_at.asc())
            )
            rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "job_id": r.job_id,
                "step_id": r.step_id,
                "state": r.state,
                "progress": r.progress,
                "completed_steps": r.completed_steps or [],
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    async def delete_checkpoints(self, job_id: str) -> int:
        """Delete all checkpoints for a job (both DB and file)."""
        async with self._session()() as session:
            result = await session.execute(
                __import__("sqlalchemy").delete(JobCheckpointOrm).where(
                    JobCheckpointOrm.job_id == job_id
                )
            )
            deleted = result.rowcount
            await session.commit()

        # Clean up files
        job_dir = os.path.join(self._checkpoint_dir, job_id)
        if os.path.isdir(job_dir):
            try:
                import shutil
                shutil.rmtree(job_dir)
            except Exception:
                pass

        return deleted
