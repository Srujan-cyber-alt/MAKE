"""Tests for the Persistent Job Manager — job lifecycle, checkpoints,
persistence, and the critical disconnect/restart/recovery scenario.
"""

import pytest

from app.intelligence.jobs.job_manager import JobManager
from app.intelligence.schemas import JobCreate, JobState, JobFailureState


class TestJobCreation:
    @pytest.mark.asyncio
    async def test_create_job(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video", priority=5))
        assert job.id is not None
        assert job.state == JobState.QUEUED
        assert job.progress == 0.0
        assert job.retry_count == 0
        assert job.created_at is not None

    @pytest.mark.asyncio
    async def test_job_has_unique_id(self, job_manager):
        j1 = await job_manager.create_job(JobCreate(request="task 1"))
        j2 = await job_manager.create_job(JobCreate(request="task 2"))
        assert j1.id != j2.id

    @pytest.mark.asyncio
    async def test_job_creation_persists(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a video", priority=1))
        retrieved = await job_manager.get_job(job.id)
        assert retrieved is not None
        assert retrieved.request == "create a video"

    @pytest.mark.asyncio
    async def test_job_with_parent(self, job_manager):
        parent = await job_manager.create_job(JobCreate(request="parent task"))
        child = await job_manager.create_job(JobCreate(request="child task", parent_job_id=parent.id))
        assert child.parent_job_id == parent.id

    @pytest.mark.asyncio
    async def test_job_has_all_required_fields(self, job_manager):
        from app.intelligence.schemas import JobCreate
        job = await job_manager.create_job(JobCreate(
            request="create a cinematic video",
            intent_category=None,
            priority=3,
            max_retries=5,
            timeout_seconds=120.0,
            project_id="proj-1",
            user_id="user-1",
            requires_approval=True,
        ))
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.priority == 3
        assert retrieved.max_retries == 5
        assert retrieved.timeout_seconds == 120.0
        assert retrieved.project_id == "proj-1"
        assert retrieved.user_id == "user-1"
        assert retrieved.requires_approval is True


class TestJobLifecycle:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        result = await job_manager.execute_job(job)
        assert result["status"] == "completed"
        final = await job_manager.get_job(job.id)
        assert final.state == JobState.COMPLETED
        assert final.progress == 1.0

    @pytest.mark.asyncio
    async def test_state_transitions_sequential(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video"))
        await job_manager.set_state(job.id, JobState.PLANNING, progress=0.1)
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.3)
        await job_manager.set_state(job.id, JobState.CHECKPOINTED, progress=0.5)
        await job_manager.set_state(job.id, JobState.COMPLETED, progress=1.0)
        final = await job_manager.get_job(job.id)
        assert final.state == JobState.COMPLETED
        assert final.progress == 1.0

    @pytest.mark.asyncio
    async def test_progress_updates(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.update_progress(job.id, 0.25, step="step1")
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.progress == 0.25

    @pytest.mark.asyncio
    async def test_state_transition_records_log(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.set_state(job.id, JobState.PLANNING, progress=0.1)
        logs = await job_manager.get_logs(job.id)
        assert len(logs) > 0
        assert all(l["level"] == "INFO" for l in logs)


class TestJobExecutionWithSteps:
    @pytest.mark.asyncio
    async def test_execution_produces_checkpoints(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)
        checkpoints = await job_manager.checkpoint_manager.list_checkpoints(job.id)
        assert len(checkpoints) > 0

    @pytest.mark.asyncio
    async def test_execution_produces_artifact(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)
        artifacts = await job_manager.artifact_manager.get_artifacts_for_job(job.id)
        assert len(artifacts) >= 1

    @pytest.mark.asyncio
    async def test_execution_produces_decision_trace(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)
        decisions = await job_manager.decision_trace.get_for_job(job.id)
        assert len(decisions) >= 3

    @pytest.mark.asyncio
    async def test_execution_produces_logs(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)
        logs = await job_manager.get_logs(job.id)
        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_execution_plan_stored(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.execute_job(job)
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.plan is not None
        assert len(retrieved.plan["steps"]) > 0


class TestRestartRecovery:
    """CRITICAL: START JOB → DISCONNECT → RESTART → RECOVER → COMPLETE"""

    @pytest.mark.asyncio
    async def test_job_survives_process_restart(self, job_manager):
        # 1. Create and run job to completion
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person at night", priority=1))
        result = await job_manager.execute_job(job)
        assert result["status"] == "completed"

        # 2. Simulate restart: fresh JobManager from the SAME persistent database
        jm2 = JobManager()

        # 3. Job should still be discoverable after restart
        recovered = await jm2.get_job(job.id)
        assert recovered is not None
        assert recovered.state == JobState.COMPLETED

    @pytest.mark.asyncio
    async def test_interrupted_job_recovery(self, job_manager):
        # 1. Create job
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))

        # 2. Start running (simulate process death mid-execution)
        await job_manager.set_state(job.id, JobState.PLANNING, progress=0.0)
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.15)

        # 3. Write checkpoint as if process died partway
        await job_manager.checkpoint_manager.create_checkpoint(
            job_id=job.id,
            step_id="recall_memory",
            state={"partial": True},
            progress=0.15,
            completed_steps=["validate_request"],
            notes="Process died here",
        )

        # 4. Simulate restart with a NEW JobManager (fresh process, same DB)
        jm2 = JobManager()

        # 5. Detect interrupted job
        interrupted = await jm2.recovery.detect_interrupted()
        assert any(j["job_id"] == job.id for j in interrupted)

        # 6. Recover the job
        recovery_result = await jm2.recovery.recover_job(job.id)
        assert recovery_result["status"] in ("recovered", "requeued")
        assert recovery_result["retry_count"] == 1

        # 7. Complete the job from the recovered state
        recovered_job = await jm2.get_job(job.id)
        result = await jm2.execute_job(recovered_job)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_recovery_preserves_checkpoints(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        await job_manager.checkpoint_manager.create_checkpoint(
            job_id=job.id, step_id="s1", state={}, progress=0.1, completed_steps=["s0"]
        )
        await job_manager.checkpoint_manager.create_checkpoint(
            job_id=job.id, step_id="s2", state={}, progress=0.2, completed_steps=["s0", "s1"]
        )

        # Restart
        jm2 = JobManager()
        interrupted = await jm2.recovery.detect_interrupted()
        assert any(j["job_id"] == job.id and j["has_checkpoint"] for j in interrupted)

        checkpoints = await jm2.checkpoint_manager.list_checkpoints(job.id)
        assert len(checkpoints) == 2

    @pytest.mark.asyncio
    async def test_reopen_make_recovers_jobs(self, job_manager):
        # Phase 1: Create jobs in various states
        job1 = await job_manager.create_job(JobCreate(request="task 1", priority=1))
        job2 = await job_manager.create_job(JobCreate(request="task 2", priority=2))

        await job_manager.set_state(job1.id, JobState.RUNNING, progress=0.3)
        await job_manager.set_state(job2.id, JobState.QUEUED)

        # Simulate restart
        jm3 = JobManager()

        # job1 should be detected as interrupted
        interrupted = await jm3.recovery.detect_interrupted()
        job_ids = {j["job_id"] for j in interrupted}
        assert job1.id in job_ids

        recovery = await jm3.recover_interrupted()
        assert any(r["status"] in ("recovered", "requeued") and r["job_id"] == job1.id for r in recovery)

        # job2 should still be queued
        recovered_job2 = await jm3.get_job(job2.id)
        assert recovered_job2.state == JobState.QUEUED

    @pytest.mark.asyncio
    async def test_no_duplicate_execution_after_recovery(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        await job_manager.checkpoint_manager.create_checkpoint(
            job_id=job.id, step_id="s1", state={}, progress=0.1, completed_steps=[]
        )

        # Restart and recover
        jm2 = JobManager()
        await jm2.recovery.recover_job(job.id)

        recovered = await jm2.get_job(job.id)
        result = await jm2.execute_job(recovered)
        assert result["status"] == "completed"

        # Only one artifact
        artifacts = await jm2.artifact_manager.get_artifacts_for_job(job.id)
        assert len(artifacts) == 1

    @pytest.mark.asyncio
    async def test_persistence_survives_across_processes(self, job_manager):
        """Full persistence test: create, disconnect, restart, verify data intact."""
        # Phase 1: Create job and execute
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person at sunset"))
        await job_manager.execute_job(job)

        # Phase 2: Simulate disconnect + restart
        jm2 = JobManager()

        # Phase 3: Verify all data persists
        job_data = await jm2.get_job_response(job.id)
        assert job_data is not None
        assert job_data.state == JobState.COMPLETED
        assert len(job_data.checkpoints) > 0

        decisions = await jm2.decision_trace.get_for_job(job.id)
        assert len(decisions) > 0

        artifacts = await jm2.artifact_manager.get_artifacts_for_job(job.id)
        assert len(artifacts) >= 1

    @pytest.mark.asyncio
    async def test_recovery_marks_paused_jobs_correctly(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.3)
        await job_manager.pause_job(job.id, "user pause")

        interrupted = await job_manager.recovery.detect_interrupted()
        paused = [j for j in interrupted if j["job_id"] == job.id]
        assert len(paused) == 1
        assert paused[0]["state"] == "paused"


class TestJobCancellation:
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test task"))
        result = await job_manager.cancel_job(job.id)
        assert result is True
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.state == JobState.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test task"))
        await job_manager.execute_job(job)
        result = await job_manager.cancel_job(job.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, job_manager):
        result = await job_manager.cancel_job("nonexistent-id")
        assert result is False


class TestRetryAndFailure:
    @pytest.mark.asyncio
    async def test_retry_count_incremented_on_recovery(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test", max_retries=5))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        result = await job_manager.recovery.recover_job(job.id)
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test", max_retries=2))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        await job_manager.recovery.recover_job(job.id)
        await job_manager.recovery.recover_job(job.id)
        result = await job_manager.recovery.recover_job(job.id)
        # After initial + 3 recoveries, retry_count=4 > max_retries=2
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_mark_failed(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        result = await job_manager.recovery.mark_failed(job.id, "test error")
        assert result is True
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.state == JobState.FAILED
        assert retrieved.error == "test error"

    @pytest.mark.asyncio
    async def test_mark_failed_recoverable(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        result = await job_manager.recovery.mark_failed(job.id, "transient error", recoverable=True)
        assert result is True
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.state == JobState.RECOVERABLE

    @pytest.mark.asyncio
    async def test_retry_job_after_failure(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.2)
        await job_manager.recovery.mark_failed(job.id, "transient error", recoverable=True)

        # Recover and re-run
        await job_manager.recovery.recover_job(job.id)
        recovered = await job_manager.get_job(job.id)
        result = await job_manager.execute_job(recovered)
        assert result["status"] == "completed"


class TestPauseResume:
    @pytest.mark.asyncio
    async def test_pause_job(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.3)
        result = await job_manager.pause_job(job.id, "user requested pause")
        assert result is True
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.state == JobState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_then_resume(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="create a cinematic video of a person"))
        await job_manager.set_state(job.id, JobState.RUNNING, progress=0.3)
        await job_manager.pause_job(job.id)

        result = await job_manager.resume_job(job.id)
        assert result is True
        retrieved = await job_manager.get_job(job.id)
        assert retrieved.state == JobState.QUEUED

        # Now execute
        final = await job_manager.execute_job(retrieved)
        assert final["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_non_paused_job_fails(self, job_manager):
        job = await job_manager.create_job(JobCreate(request="test"))
        result = await job_manager.resume_job(job.id)
        assert result is False


class TestJobListing:
    @pytest.mark.asyncio
    async def test_list_jobs(self, job_manager):
        await job_manager.create_job(JobCreate(request="task 1"))
        await job_manager.create_job(JobCreate(request="task 2"))
        jobs = await job_manager.list_jobs()
        assert len(jobs) >= 2

    @pytest.mark.asyncio
    async def test_list_jobs_by_state(self, job_manager):
        await job_manager.create_job(JobCreate(request="task 1"))
        j2 = await job_manager.create_job(JobCreate(request="task 2"))
        await job_manager.execute_job(j2)
        queued = await job_manager.list_jobs(state=JobState.QUEUED)
        completed = await job_manager.list_jobs(state=JobState.COMPLETED)
        assert len(queued) >= 1
        assert len(completed) == 1


class TestScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_priority_ordering(self, job_manager):
        await job_manager.create_job(JobCreate(request="low", priority=1))
        await job_manager.create_job(JobCreate(request="high", priority=10))
        await job_manager.create_job(JobCreate(request="med", priority=5))
        next_job = await job_manager.scheduler.next_job()
        assert next_job.request == "high"

    @pytest.mark.asyncio
    async def test_scheduler_fifo_within_priority(self, job_manager):
        await job_manager.create_job(JobCreate(request="first", priority=5))
        await job_manager.create_job(JobCreate(request="second", priority=5))
        j1 = await job_manager.scheduler.next_job()
        assert j1.request == "first"

    @pytest.mark.asyncio
    async def test_scheduler_concurrency_control(self, job_manager):
        await job_manager.create_job(JobCreate(request="t1"))
        await job_manager.create_job(JobCreate(request="t2"))
        await job_manager.create_job(JobCreate(request="t3"))
        assert job_manager.scheduler.max_concurrent == 3
        summary = job_manager.scheduler.schedule_summary()
        assert summary["available_slots"] == 3

    @pytest.mark.asyncio
    async def test_scheduler_acquire_release_slot(self, job_manager):
        scheduler = job_manager.scheduler
        acquired = await scheduler.acquire_slot("job-1")
        assert acquired is True
        summary = scheduler.schedule_summary()
        assert summary["available_slots"] == 2
        await scheduler.release_slot("job-1")
        summary = scheduler.schedule_summary()
        assert summary["available_slots"] == 3

    @pytest.mark.asyncio
    async def test_scheduler_acquire_slot_full(self, job_manager):
        scheduler = job_manager.scheduler
        await scheduler.acquire_slot("j1")
        await scheduler.acquire_slot("j2")
        await scheduler.acquire_slot("j3")
        result = await scheduler.acquire_slot("j4")
        assert result is False
