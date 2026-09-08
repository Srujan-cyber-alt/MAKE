"""Tests for concurrent job execution and failure isolation."""

import asyncio
import pytest

from app.intelligence.jobs.job_manager import JobManager
from app.intelligence.schemas import JobCreate, JobState


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_multiple_concurrent_jobs(self, job_manager):
        jobs = []
        for i in range(5):
            job = await job_manager.create_job(JobCreate(request=f"create cinematic video {i}", priority=i))
            jobs.append(job)

        # Execute all jobs concurrently
        results = await asyncio.gather(*[job_manager.execute_job(j) for j in jobs])

        assert all(r["status"] == "completed" for r in results)
        for j in jobs:
            retrieved = await job_manager.get_job(j.id)
            assert retrieved.state == JobState.COMPLETED

    @pytest.mark.asyncio
    async def test_concurrent_jobs_dont_interfere(self, job_manager):
        job1 = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        job2 = await job_manager.create_job(JobCreate(request="create a cinematic video of a sunset"))

        result1, result2 = await asyncio.gather(
            job_manager.execute_job(job1),
            job_manager.execute_job(job2),
        )

        assert result1["status"] == "completed"
        assert result2["status"] == "completed"

        j1 = await job_manager.get_job(job1.id)
        j2 = await job_manager.get_job(job2.id)
        assert j1.state == JobState.COMPLETED
        assert j2.state == JobState.COMPLETED
        # Ensure plans didn't get mixed up
        assert j1.plan is not None
        assert j2.plan is not None
        assert j1.plan["intent_id"] != j2.plan["intent_id"]

    @pytest.mark.asyncio
    async def test_failed_job_doesnt_affect_others(self, job_manager):
        # Create a failing job by manually setting it to FAILED
        job_fail = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.set_state(job_fail.id, JobState.FAILED, error="simulated failure")

        # Create and run a normal job
        job_ok = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        result = await job_manager.execute_job(job_ok)

        assert result["status"] == "completed"
        ok = await job_manager.get_job(job_ok.id)
        assert ok.state == JobState.COMPLETED
        fail = await job_manager.get_job(job_fail.id)
        assert fail.state == JobState.FAILED

    @pytest.mark.asyncio
    async def test_cancellation_during_execution(self, job_manager):
        """A cancelled job should not block other jobs."""
        job_cancel = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        job_other = await job_manager.create_job(JobCreate(request="create a cinematic video of a sunset"))

        # Start both jobs, then cancel one
        task_cancel = asyncio.create_task(job_manager.execute_job(job_cancel))
        task_other = asyncio.create_task(job_manager.execute_job(job_other))

        # Cancel the first job
        await asyncio.sleep(0.05)
        await job_manager.cancel_job(job_cancel.id)

        result_other = await task_other
        assert result_other["status"] == "completed"

    @pytest.mark.asyncio
    async def test_retry_doesnt_create_duplicate_after_success(self, job_manager):
        """Once a job completes, it cannot be retried."""
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)

        # Attempting recovery should not create duplicate execution
        result = await job_manager.recovery.recover_job(job.id)
        assert result["status"] == "not_needed"  # or similar

    @pytest.mark.asyncio
    async def test_scheduler_respects_priority_under_load(self, job_manager):
        """Higher-priority jobs should execute first even when created after lower ones."""
        await job_manager.create_job(JobCreate(request="low_priority", priority=1))
        await job_manager.create_job(JobCreate(request="med_priority", priority=5))
        await job_manager.create_job(JobCreate(request="high_priority", priority=10))

        scheduler = job_manager.scheduler
        results = []
        for _ in range(3):
            j = await scheduler.next_job()
            assert j is not None
            results.append((j.request, j.priority))

        # Order should be by priority (highest first) within same priority, FIFO
        assert results[0][0] == "high_priority"
        assert results[0][1] == 10

    @pytest.mark.asyncio
    async def test_starvation_prevention(self, job_manager):
        """Repeated high-priority jobs shouldn't starve lower ones."""
        scheduler = job_manager.scheduler
        for i in range(10):
            await job_manager.create_job(JobCreate(request=f"high_{i}", priority=10))
        await job_manager.create_job(JobCreate(request="low_priority", priority=1))

        # Should eventually get the low-priority job
        retrieved_low = False
        attempts = 0
        while attempts < 20 and not retrieved_low:
            j = await scheduler.next_job()
            if j and j.request == "low_priority":
                retrieved_low = True
            attempts += 1
        assert retrieved_low
