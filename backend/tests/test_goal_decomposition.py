"""Tests for the Goal Decomposer module."""

import pytest
from app.intelligence.agent.goal_decomposer import (
    GoalDecomposer, TaskDefinition, TaskType, TaskPriority, ResourceEstimate
)


class TestGoalDecomposer:
    def test_create_decomposer(self):
        decomposer = GoalDecomposer()
        assert decomposer is not None

    def test_decompose_simple_goal(self):
        decomposer = GoalDecomposer()
        tasks = decomposer.decompose("Create a product launch campaign.", constraints={})
        assert len(tasks) > 0
        assert all(isinstance(t, TaskDefinition) for t in tasks)

    def test_decompose_returns_phases(self):
        decomposer = GoalDecomposer()
        tasks = decomposer.decompose("Build a web application.", constraints={})
        task_types = {t.task_type for t in tasks}
        assert TaskType.RESEARCH in task_types or TaskType.COMPUTE in task_types

    def test_task_definition_fields(self):
        decomposer = GoalDecomposer()
        tasks = decomposer.decompose("Analyze data and generate report.", constraints={})
        for task in tasks:
            assert task.id is not None
            assert task.name
            assert task.objective
            assert task.task_type in TaskType
            assert isinstance(task.priority, TaskPriority)

    def test_decompose_deterministic(self):
        decomposer = GoalDecomposer()
        tasks1 = decomposer.decompose("Same goal", constraints={})
        tasks2 = decomposer.decompose("Same goal", constraints={})
        assert len(tasks1) == len(tasks2)


class TestTaskType:
    def test_task_type_values(self):
        assert TaskType.COMPUTE.value == "compute"
        assert TaskType.DATA_FETCH.value == "data_fetch"
        assert TaskType.RESEARCH.value == "research"

    def test_task_priority_values(self):
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.HIGH.value == "high"


class TestResourceEstimate:
    def test_resource_estimate_defaults(self):
        estimate = ResourceEstimate()
        assert estimate.cpu_cores == 0.0
        assert estimate.memory_mb == 0
        assert estimate.estimated_duration_seconds == 0.0

    def test_resource_estimate_custom(self):
        estimate = ResourceEstimate(cpu_cores=2.0, memory_mb=512, estimated_duration_seconds=60.0)
        assert estimate.cpu_cores == 2.0
        assert estimate.memory_mb == 512
        assert estimate.estimated_duration_seconds == 60.0
