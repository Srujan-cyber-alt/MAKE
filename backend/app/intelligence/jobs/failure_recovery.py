"""Failure Recovery — detects and recovers interrupted jobs.

After a process restart or session disconnect, the recovery system scans
for jobs in incomplete states and resumes them from their last checkpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_

from app.intelligence.schemas import JobState, JobFailureState
from app.intelligence.models import IntelligenceJob
from app.intelligence.jobs.checkpoint_manager import CheckpointManager


# States that indicate a job was interrupted and may be recoverable
INTERRUPTED_STATES = {
    JobState.RUNNING,
    JobState.PLANNING,
    JobState.CHECKPOINTED,
    JobState.PAUSED,
    JobState.RECOVERABLE,
}


class FailureRecovery:
    """Detects and recovers interrupted/failed jobs."""

    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        self._checkpoints = checkpoint_manager or CheckpointManager()

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    async def detect_interrupted(self) -> List[Dict[str, Any]]:
        """Find all jobs that were running/planning/checkpointed when the
        process died (session disconnect simulated by process exit)."""
        async with self._session()() as session:
            result = await session.execute(
                select(IntelligenceJob)
                .where(IntelligenceJob.state.in_(list(INTERRUPTED_STATES)))
                .order_by(IntelligenceJob.updated_at.desc())
            )
            jobs = result.scalars().all()

        detected: List[Dict[str, Any]] = []
        for job in jobs:
            checkpoint = await self._checkpoints.load_latest_checkpoint(job.id)
            detected.append({
                "job_id": job.id,
                "state": job.state.value,
                "failure_state": job.failure_state.value if job.failure_state else None,
                "progress": job.progress,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "has_checkpoint": checkpoint is not None,
                "last_checkpoint_step": checkpoint["step_id"] if checkpoint else None,
                "last_checkpoint_progress": checkpoint["progress"] if checkpoint else 0.0,
                "updated_at": job.updated_at,
                "error": job.error,
            })
        return detected

    async def recover_job(self, job_id: str) -> Dict[str, Any]:
        """Attempt to recover a single job from its last checkpoint."""
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return {"job_id": job_id, "status": "not_found"}

            checkpoint = await self._checkpoints.load_latest_checkpoint(job_id)

            if job.retry_count >= job.max_retries:
                job.state = JobState.FAILED
                job.failure_state = JobFailureState.FAILED
                job.error = "Max retries exceeded during recovery"
                await session.commit()
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "reason": "max_retries_exceeded",
                    "retry_count": job.retry_count,
                }

            if checkpoint:
                # Resume from checkpoint
                job.state = JobState.RUNNING
                job.failure_state = JobFailureState.RECOVERABLE
                job.retry_count = job.retry_count + 1
                job.resumable_state = {
                    "checkpoint_id": checkpoint["id"],
                    "last_step": checkpoint["step_id"],
                    "completed_steps": checkpoint["completed_steps"],
                    "state": checkpoint["state"],
                    "progress": checkpoint["progress"],
                    "recovered_at": datetime.utcnow().isoformat(),
                }
                await session.commit()
                return {
                    "job_id": job_id,
                    "status": "recovered",
                    "resumed_from_checkpoint": True,
                    "checkpoint_step": checkpoint["step_id"],
                    "progress": checkpoint["progress"],
                    "retry_count": job.retry_count,
                }
            else:
                # No checkpoint — re-queue from start
                if job.retry_count >= job.max_retries:
                    job.state = JobState.FAILED
                    job.failure_state = JobFailureState.FAILED
                    job.error = "No checkpoint and max retries exceeded"
                    await session.commit()
                    return {"job_id": job_id, "status": "failed", "reason": "no_checkpoint_max_retries"}

                job.state = JobState.QUEUED
                job.failure_state = JobFailureState.RECOVERABLE
                job.retry_count = job.retry_count + 1
                job.resumable_state = {
                    "recovered_at": datetime.utcnow().isoformat(),
                    "restart_from_beginning": True,
                }
                await session.commit()
                return {
                    "job_id": job_id,
                    "status": "requeued",
                    "resumed_from_checkpoint": False,
                    "retry_count": job.retry_count,
                }

    async def recover_all(self) -> List[Dict[str, Any]]:
        """Recover all interrupted jobs."""
        interrupted = await self.detect_interrupted()
        results: List[Dict[str, Any]] = []
        for info in interrupted:
            result = await self.recover_job(info["job_id"])
            results.append(result)
        return results

    async def mark_failed(self, job_id: str, error: str, recoverable: bool = False) -> bool:
        """Mark a job as failed (optionally recoverable)."""
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            job.state = JobState.RECOVERABLE if recoverable else JobState.FAILED
            job.failure_state = JobFailureState.RECOVERABLE if recoverable else JobFailureState.FAILED
            job.error = error
            job.completed_at = datetime.utcnow()
            await session.commit()
        return True

    async def pause_job(self, job_id: str, reason: str = "") -> bool:
        """Pause a job (can be resumed later)."""
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            if job.state not in (JobState.RUNNING, JobState.PLANNING, JobState.QUEUED, JobState.CHECKPOINTED):
                return False
            job.state = JobState.PAUSED
            job.failure_state = JobFailureState.PAUSED
            if reason:
                job.error = reason
            await session.commit()
        return True

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            if job.state != JobState.PAUSED:
                return False
            job.state = JobState.QUEUED
            job.failure_state = None
            await session.commit()
        return True
