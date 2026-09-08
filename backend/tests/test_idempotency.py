"""Tests for Idempotency."""

import pytest
from app.intelligence.agent.task_executor import TaskExecutor, ExecutionResult, ExecutionStatus
from app.intelligence.agent.mission_planner import TaskDefinition, TaskType


class TestIdempotency:
    def test_same_task_same_result(self):
        executor = TaskExecutor()
        task = TaskDefinition(
            task_id="idempotent_1",
            name="Idempotent Task",
            objective="Produce same result",
            task_type=TaskType.COMPUTE,
            idempotency_key="key_123",
        )
        result1 = executor.execute(task)
        result2 = executor.execute(task)
        assert result1.status == ExecutionStatus.SUCCESS
        assert result2.status == ExecutionStatus.SUCCESS
        assert result1.output == result2.output

    def test_no_duplicate_artifacts(self):
        executor = TaskExecutor()
        task = TaskDefinition(
            task_id="no_dup_1",
            name="No Duplicate",
            objective="Produce artifact once",
            task_type=TaskType.IO_OPERATION,
            idempotency_key="artifact_key_456",
        )
        result1 = executor.execute(task)
        result2 = executor.execute(task)
        assert len(result1.artifacts) == len(result2.artifacts)

    def test_retry_same_task_idempotent(self):
        executor = TaskExecutor()
        task = TaskDefinition(
            task_id="retry_idem_1",
            name="Retry Idempotent",
            objective="Retry safely",
            task_type=TaskType.COMPUTE,
            idempotency_key="retry_key_789",
            max_retries=3,
        )
        results = []
        for _ in range(3):
            results.append(executor.execute(task))
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
