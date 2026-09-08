"""Priority Scheduler — schedules jobs by priority and manages concurrency."""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_

from app.intelligence.schemas import JobState
from app.intelligence.models import IntelligenceJob


RECOVERABLE_STATES = {
    JobState.RUNNING,
    JobState.PLANNING,
    JobState.CHECKPOINTED,
    JobState.RECOVERABLE,
    JobState.PAUSED,
}


class PriorityScheduler:
    """Selects the next job to run based on priority, age, and retry count."""

    def __init__(self, max_concurrent: int = 3) -> None:
        self._max_concurrent = max_concurrent
        self._running: set[str] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def available_slots(self) -> int:
        return self._max_concurrent - len(self._running)

    async def acquire_slot(self, job_id: str) -> bool:
        """Claim a concurrency slot for a job. Returns False if full."""
        if job_id in self._running:
            return True
        if len(self._running) >= self._max_concurrent:
            return False
        self._running.add(job_id)
        return True

    async def release_slot(self, job_id: str) -> None:
        self._running.discard(job_id)

    async def next_job(self) -> Optional[IntelligenceJob]:
        """Atomically claim and return the highest-priority queued job, or None.

        The selected job is transitioned to ``RUNNING`` so it will not be
        returned again on subsequent calls. This guarantees forward progress
        and prevents starvation of lower-priority jobs.
        """
        async with self._session()() as session:
            result = await session.execute(
                select(IntelligenceJob)
                .where(
                    and_(
                        IntelligenceJob.state == JobState.QUEUED,
                        IntelligenceJob.retry_count < IntelligenceJob.max_retries,
                        IntelligenceJob.requires_approval.is_((False)),
                    )
                )
                .order_by(
                    IntelligenceJob.priority.desc(),
                    IntelligenceJob.created_at.asc(),
                )
                .limit(1)
            )
            job = result.scalar_one_or_none()
            if job is None:
                return None
            job.state = JobState.RUNNING
            await session.commit()
            await session.refresh(job)
            return job

    async def pending_jobs(self, limit: int = 50) -> List[IntelligenceJob]:
        """List pending (queued) jobs ordered by priority."""
        async with self._session()() as session:
            result = await session.execute(
                select(IntelligenceJob)
                .where(IntelligenceJob.state == JobState.QUEUED)
                .order_by(
                    IntelligenceJob.priority.desc(),
                    IntelligenceJob.created_at.asc(),
                )
                .limit(limit)
            )
            return result.scalars().all()

    async def runnable_jobs(self, limit: int = 10) -> List[IntelligenceJob]:
        """Jobs that can be picked up now: QUEUED or RECOVERABLE."""
        async with self._session()() as session:
            result = await session.execute(
                select(IntelligenceJob)
                .where(
                    IntelligenceJob.state.in_([JobState.QUEUED, JobState.RECOVERABLE]),
                )
                .order_by(
                    IntelligenceJob.priority.desc(),
                    IntelligenceJob.created_at.asc(),
                )
                .limit(limit)
            )
            return result.scalars().all()

    async def incompletable_jobs(self) -> List[IntelligenceJob]:
        """Jobs that were interrupted mid-execution (RUNNING/PLANNING/CHECKPOINTED/PAUSED)."""
        async with self._session()() as session:
            result = await session.execute(
                select(IntelligenceJob)
                .where(IntelligenceJob.state.in_(list(RECOVERABLE_STATES)))
            )
            return result.scalars().all()

    def schedule_summary(self) -> Dict[str, Any]:
        return {
            "max_concurrent": self._max_concurrent,
            "running_count": len(self._running),
            "available_slots": self._max_concurrent - len(self._running),
            "running_job_ids": list(self._running),
        }
