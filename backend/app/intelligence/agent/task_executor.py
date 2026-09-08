from typing import Any, Dict, Optional, Callable
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from asyncio import Semaphore, TimeoutError as AioTimeoutError
from .task_graph import GraphNode
from .mission_planner import TaskDefinition
from .resource_manager import ResourceManager
from .observation_engine import ObservationEngine
from .types import ExecutionResult, ExecutionStatus


class TaskExecutor:
    def __init__(self, max_concurrency: int = 4) -> None:
        self.max_concurrency = max_concurrency
        self._semaphore = Semaphore(max_concurrency)
        self._task_registry: Dict[str, Callable] = {}
        self._running_tasks: Dict[UUID, ExecutionResult] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._task_registry["compute"] = self._default_compute_handler
        self._task_registry["data_fetch"] = self._default_data_fetch_handler
        self._task_registry["transformation"] = self._default_transformation_handler
        self._task_registry["validation"] = self._default_validation_handler
        self._task_register["io_operation"] = self._default_io_handler
        self._task_registry["research"] = self._default_research_handler
        self._task_registry["integration"] = self._default_integration_handler

    async def execute(self, task: TaskDefinition, timeout: Optional[float] = None) -> ExecutionResult:
        timeout = timeout or task.timeout_seconds
        async with self._semaphore:
            try:
                if task.idempotency_key and task.idempotency_key in self._running_tasks:
                    return self._running_tasks[task.idempotency_key]
                handler = self._task_registry.get(task.task_type.value, self._default_compute_handler)
                if timeout:
                    result = await asyncio.wait_for(handler(task), timeout=timeout)
                else:
                    result = await handler(task)
                if task.idempotency_key:
                    self._running_tasks[task.idempotency_key] = result
                return result
            except AioTimeoutError:
                return ExecutionResult(
                    task_id=str(task.id),
                    status=ExecutionStatus.TIMEOUT,
                    error="Task execution timed out",
                    attempts=1,
                )
            except Exception as e:
                return ExecutionResult(
                    task_id=str(task.id),
                    status=ExecutionStatus.FAILURE,
                    error=str(e),
                    attempts=1,
                )

    async def _default_compute_handler(self, task: TaskDefinition) -> ExecutionResult:
        import time
        start = time.time()
        result = await asyncio.to_thread(lambda: {"computed": True, "task": task.name})
        duration = (time.time() - start) * 1000
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output=result,
            duration_ms=duration,
            attempts=1,
        )

    async def _default_data_fetch_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"fetched": True, "task": task.name},
            attempts=1,
        )

    async def _default_transformation_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"transformed": True, "task": task.name},
            attempts=1,
        )

    async def _default_validation_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"validated": True, "task": task.name},
            attempts=1,
        )

    async def _default_io_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"io": True, "task": task.name},
            attempts=1,
        )

    async def _default_research_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"researched": True, "task": task.name},
            attempts=1,
        )

    async def _default_integration_handler(self, task: TaskDefinition) -> ExecutionResult:
        return ExecutionResult(
            task_id=str(task.id),
            status=ExecutionStatus.SUCCESS,
            output={"integrated": True, "task": task.name},
            attempts=1,
        )

    def register_handler(self, task_type: str, handler: Callable) -> None:
        self._task_registry[task_type] = handler
