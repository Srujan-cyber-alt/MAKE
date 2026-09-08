"""Tests for Checkpoint Manager."""

import json
import os
import pytest

from app.intelligence.jobs.checkpoint_manager import CheckpointManager


class TestCheckpointManager:
    @pytest.fixture
    def cm(self, intel_db):
        from app.intelligence.jobs.job_manager import JobManager
        jm = JobManager()
        return jm.checkpoint_manager

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, cm):
        cp = await cm.create_checkpoint(
            job_id="job-1", step_id="step1", state={"k": "v"}, progress=0.5, completed_steps=["s0"]
        )
        assert cp["id"] is not None
        assert cp["job_id"] == "job-1"
        assert cp["step_id"] == "step1"
        assert cp["progress"] == 0.5
        assert cp["completed_steps"] == ["s0"]

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, cm):
        await cm.create_checkpoint(job_id="job-1", step_id="s1", state={}, progress=0.1, completed_steps=[])
        await cm.create_checkpoint(job_id="job-1", step_id="s2", state={}, progress=0.2, completed_steps=["s1"])
        await cm.create_checkpoint(job_id="job-2", step_id="s1", state={}, progress=0.1, completed_steps=[])
        result = await cm.list_checkpoints("job-1")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_resume_checkpoint(self, cm):
        await cm.create_checkpoint(job_id="job-1", step_id="s1", state={"data": 1}, progress=0.1, completed_steps=[])
        import asyncio
        await asyncio.sleep(0.01)
        cp2 = await cm.create_checkpoint(job_id="job-1", step_id="s2", state={"data": 2}, progress=0.2, completed_steps=["s1"])
        resumed = await cm.resume_checkpoint("job-1")
        assert resumed is not None
        assert resumed["step_id"] == "s2"

    @pytest.mark.asyncio
    async def test_get_checkpoint(self, cm):
        cp = await cm.create_checkpoint(job_id="job-1", step_id="s1", state={}, progress=0.1, completed_steps=[])
        # Verify file exists
        import shutil
        job_dir = os.path.join(cm._checkpoint_dir, "job-1")
        assert os.path.isdir(job_dir)
        files = os.listdir(job_dir)
        assert len(files) == 1
        with open(os.path.join(job_dir, files[0])) as f:
            file_data = json.load(f)
        assert file_data["id"] == cp["id"]

    @pytest.mark.asyncio
    async def test_checkpoint_files_written(self, cm):
        cp = await cm.create_checkpoint(
            job_id="job-1", step_id="s1", state={"complex": [1, 2, 3]}, progress=0.1, completed_steps=[]
        )
        job_dir = os.path.join(cm._checkpoint_dir, "job-1")
        assert os.path.isdir(job_dir)
        for f in os.listdir(job_dir):
            with open(os.path.join(job_dir, f)) as fh:
                data = json.load(fh)
            assert data["id"] == cp["id"]
            assert data["state"]["complex"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_latest_checkpoint(self, cm):
        await cm.create_checkpoint(job_id="job-1", step_id="s1", state={}, progress=0.1, completed_steps=[])
        import asyncio
        await asyncio.sleep(0.01)
        cp2 = await cm.create_checkpoint(job_id="job-1", step_id="s2", state={}, progress=0.2, completed_steps=["s1"])
        latest = await cm.resume_checkpoint("job-1")
        assert latest is not None
        assert latest["id"] == cp2["id"]

    @pytest.mark.asyncio
    async def test_delete_checkpoints_for_job(self, cm):
        await cm.create_checkpoint(job_id="job-1", step_id="s1", state={}, progress=0.1, completed_steps=[])
        await cm.create_checkpoint(job_id="job-1", step_id="s2", state={}, progress=0.2, completed_steps=["s1"])
        deleted = await cm.delete_checkpoints_for_job("job-1")
        assert deleted == 2
        remaining = await cm.list_checkpoints("job-1")
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_corrupted_checkpoint_file_handling(self, cm):
        """Test that corrupted JSON files don't crash recovery."""
        cp = await cm.create_checkpoint(
            job_id="job-1", step_id="s1", state={"data": 1}, progress=0.1, completed_steps=[]
        )
        job_dir = os.path.join(cm._checkpoint_dir, "job-1")
        files = os.listdir(job_dir)
        assert len(files) == 1
        # Corrupt the file
        with open(os.path.join(job_dir, files[0]), "w") as f:
            f.write("CORRUPTED JSON{{{")
        # Listing checkpoints from DB should still work
        checkpoints = await cm.list_checkpoints("job-1")
        assert len(checkpoints) == 1
        # Verify DB is source of truth even when file is corrupted
        assert checkpoints[0]["step_id"] == "s1"

    @pytest.mark.asyncio
    async def test_checkpoint_with_complex_state(self, cm):
        """Checkpoints must serialize complex nested state."""
        state = {
            "plan": {"steps": [{"id": "1", "name": "test"}], "nested": {"a": [1, 2]}},
            "meta": {"ts": "2024-01-01"},
        }
        cp = await cm.create_checkpoint(
            job_id="job-1", step_id="s1", state=state, progress=0.5, completed_steps=["s0"]
        )
        assert cp["state"]["plan"]["steps"][0]["id"] == "1"
        assert cp["state"]["plan"]["nested"]["a"] == [1, 2]
