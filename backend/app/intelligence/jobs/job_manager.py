"""Persistent Job Manager — the central job lifecycle controller.

Job states:
    QUEUED → PLANNING → RUNNING → CHECKPOINTED → COMPLETED

Failure states:
    PAUSED / FAILED / CANCELLED / RECOVERABLE

Every job persists:
    - unique job ID
    - creation timestamp
    - current state (and failure sub-state)
    - progress
    - checkpoints
    - logs
    - inputs
    - outputs
    - errors
    - retry count
    - provenance
    - resumable state

A UI/session disconnect never deletes the underlying job. Reopening MAKE
allows recovery of previously running jobs.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator, Callable
from dataclasses import dataclass, field

from sqlalchemy import select, update, delete, and_, func

from app.intelligence.config import intelligence_settings
from app.intelligence.schemas import (
    JobCreate, JobState, JobFailureState, JobResponse, PlanStatus,
    ExecutionRequest, ExecutionResult, IntentResult,
    CreativeDecision, VisualPlan, Plan,
)
from app.intelligence.models import IntelligenceJob, JobLogOrm
from app.intelligence.jobs.checkpoint_manager import CheckpointManager
from app.intelligence.jobs.artifact_manager import ArtifactManager
from app.intelligence.jobs.priority_scheduler import PriorityScheduler
from app.intelligence.jobs.failure_recovery import FailureRecovery
from app.intelligence.core.intent_engine import IntentEngine
from app.intelligence.core.reasoning_engine import ReasoningEngine
from app.intelligence.core.consistency_engine import ConsistencyEngine
from app.intelligence.core.creative_director import CreativeDirector
from app.intelligence.core.visual_planning import VisualPlanningEngine
from app.intelligence.core.self_critique import SelfCritiqueLoop
from app.intelligence.core.decision_trace import DecisionTrace
from app.intelligence.core.tool_router import ToolRouter, ToolAdapter
from app.intelligence.core.world_memory import WorldMemory
from app.intelligence.core.reality_graph import RealityGraph
from app.intelligence.core.personal_context import PersonalContext


async def _null_exec(request: ExecutionRequest) -> ExecutionResult:
    """Default no-op executor used when no tool adapter is registered.

    Does NOT fabricate AI outputs — records that the plan was executed
    but no concrete generation adapter was available.
    """
    return ExecutionResult(
        tool=request.tool,
        success=True,
        artifacts=[{"type": "plan_only", "note": "No execution adapter registered; plan recorded only"}],
        metadata={"simulated": True},
    )


class JobRunner:
    """Runs a single job's execution lifecycle.

    The runner is pluggable: each step either calls a registered tool adapter
    or the provided ``executor`` callback. This keeps the system CPU-native
    and avoids fabricating AI outputs.
    """

    def __init__(
        self,
        job_id: str,
        checkpoint_mgr: CheckpointManager,
        artifact_mgr: ArtifactManager,
        decision_trace: DecisionTrace,
        tool_router: ToolRouter,
        log_fn: Optional[Callable] = None,
    ):
        self.job_id = job_id
        self._checkpoints = checkpoint_mgr
        self._artifacts = artifact_mgr
        self._trace = decision_trace
        self._router = tool_router
        self._log = log_fn or (lambda level, msg, **kw: None)
        self._cancelled = False

    async def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    async def run_step(
        self,
        plan,
        step_index: int,
        resumable_state: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a single plan step, writing a checkpoint."""
        step = plan.steps[step_index]
        self._log("INFO", f"Executing step {step.id}: {step.description}", step_id=step.id)

        await self._trace.record(
            step=f"step_{step.action}",
            decision=f"Execute {step.action} via {step.tool.value}",
            reasoning=f"Plan step {step_index + 1}/{len(plan.steps)}",
            job_id=self.job_id,
            details={"step_id": step.id, "tool": step.tool.value},
        )

        request = ExecutionRequest(
            tool=step.tool,
            action=step.action,
            inputs=step.inputs,
            parameters=step.parameters,
            timeout_seconds=step.timeout_seconds,
        )

        adapter = self._router.get_adapter(step.tool)
        if adapter is not None:
            result = await adapter.execute(request)
        else:
            result = await _null_exec(request)

        return {
            "step_id": step.id,
            "action": step.action,
            "result": result.model_dump(),
            "completed_at": datetime.utcnow().isoformat(),
        }


class JobManager:
    """Top-level persistent job orchestrator.

    Handles job creation, state transitions, checkpoint persistence,
    log aggregation, and recovery coordination.
    """

    def __init__(
        self,
        tool_router: Optional[ToolRouter] = None,
        db_session_factory=None,
    ):
        self._tool_router = tool_router or ToolRouter()
        self._checkpoints = CheckpointManager()
        self._artifacts = ArtifactManager()
        self._scheduler = PriorityScheduler(max_concurrent=3)
        self._recovery = FailureRecovery(self._checkpoints)
        self._intent_engine = IntentEngine()
        self._reasoning = ReasoningEngine(
            intent_engine=self._intent_engine,
            consistency_engine=ConsistencyEngine(),
        )
        self._creative_director = CreativeDirector()
        self._visual_planner = VisualPlanningEngine()
        self._self_critique = SelfCritiqueLoop(self._reasoning.consistency_engine)
        self._decision_trace = DecisionTrace()
        self._world_memory = WorldMemory()
        self._reality_graph = RealityGraph()
        self._personal_context = PersonalContext()
        self._running: Dict[str, JobRunner] = {}
        self._lock = asyncio.Lock()
        self._running_jobs: Dict[str, asyncio.Task] = {}

    # ---- DB session ----

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    # ---- Job creation ----

    async def create_job(self, spec: JobCreate) -> IntelligenceJob:
        """Create a new persistent job in QUEUED state."""
        async with self._session()() as session:
            job = IntelligenceJob(
                id=str(uuid.uuid4()),
                parent_job_id=spec.parent_job_id,
                user_id=spec.user_id,
                project_id=spec.project_id,
                request=spec.request,
                intent_category=spec.intent_category.value if spec.intent_category else None,
                state=JobState.QUEUED,
                priority=spec.priority,
                retry_count=0,
                max_retries=spec.max_retries,
                timeout_seconds=spec.timeout_seconds,
                requires_approval=spec.requires_approval,
                approved=not spec.requires_approval,
                inputs=spec.inputs,
                parameters=spec.parameters,
                resumable_state=None,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

        await self._log(job.id, "INFO", f"Job created: {spec.request}")
        return job

    async def create_job_from_intent(self, intent_result: IntentResult, parameters: Optional[Dict[str, Any]] = None) -> IntelligenceJob:
        """Create a job directly from a parsed intent."""
        spec = JobCreate(
            request=intent_result.intent.raw_request,
            intent_category=intent_result.intent.category,
            priority=intent_result.intent.priority,
            parameters=parameters or {},
            inputs={"intent": intent_result.intent.model_dump()},
        )
        job = await self.create_job(spec)
        async with self._session()() as session:
            j = await session.get(IntelligenceJob, job.id)
            j.intent = intent_result.intent.model_dump()
            await session.commit()
        return job

    # ---- State transitions ----

    async def set_state(
        self,
        job_id: str,
        state: JobState,
        failure_state: Optional[JobFailureState] = None,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        resumable_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            job.state = state
            if failure_state is not None:
                job.failure_state = failure_state
            if progress is not None:
                job.progress = progress
            if error is not None:
                job.error = error
            if resumable_state is not None:
                job.resumable_state = resumable_state
            if state in (JobState.RUNNING, JobState.CHECKPOINTED) and job.started_at is None:
                job.started_at = datetime.utcnow()
            if state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                job.completed_at = datetime.utcnow()
            await session.commit()
        await self._log(job_id, "INFO", f"State transition: {state.value}", extra={"progress": progress, "error": error})
        return True

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        step: Optional[str] = None,
        state: Optional[JobState] = None,
    ) -> bool:
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            job.progress = progress
            if step:
                job.stage = step
            if state:
                job.state = state
            await session.commit()
        return True

    async def update_plan(self, job_id: str, plan: Plan) -> bool:
        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            job.plan = plan.model_dump()
            job.plan_status = plan.status
            await session.commit()
        return True

    # ---- Job queries ----

    async def get_job(self, job_id: str) -> Optional[IntelligenceJob]:
        async with self._session()() as session:
            return await session.get(IntelligenceJob, job_id)

    async def get_job_response(self, job_id: str) -> Optional[JobResponse]:
        job = await self.get_job(job_id)
        if job is None:
            return None
        checkpoints = await self._checkpoints.list_checkpoints(job_id)
        plan = None
        if job.plan:
            plan = Plan(**job.plan)
        intent = None
        if job.intent:
            intent = IntentResult(intent=Intent(**job.intent))
        return JobResponse(
            job_id=job.id,
            state=job.state,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            intent=intent.intent if intent else None,
            plan=plan,
            result=job.result,
            error=job.error,
            retry_count=job.retry_count,
            checkpoints=checkpoints,
        )

    async def list_jobs(
        self,
        state: Optional[JobState] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[IntelligenceJob]:
        async with self._session()() as session:
            stmt = select(IntelligenceJob)
            conditions = []
            if state:
                conditions.append(IntelligenceJob.state == state)
            if user_id:
                conditions.append(IntelligenceJob.user_id == user_id)
            if project_id:
                conditions.append(IntelligenceJob.project_id == project_id)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.order_by(IntelligenceJob.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job. Running executors are signalled to stop."""
        runner = self._running.get(job_id)
        if runner:
            await runner.cancel()

        async with self._session()() as session:
            job = await session.get(IntelligenceJob, job_id)
            if job is None:
                return False
            if job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                return False
            job.state = JobState.CANCELLED
            job.failure_state = JobFailureState.CANCELLED
            job.completed_at = datetime.utcnow()
            await session.commit()

        await self._log(job_id, "WARNING", "Job cancelled")
        if job_id in self._running_jobs:
            self._running_jobs[job_id].cancel()
            del self._running_jobs[job_id]
        return True

    async def pause_job(self, job_id: str, reason: str = "") -> bool:
        return await self._recovery.pause_job(job_id, reason)

    async def resume_job(self, job_id: str) -> bool:
        return await self._recovery.resume_job(job_id)

    # ---- Recovery ----

    async def recover_interrupted(self) -> List[Dict[str, Any]]:
        """On restart, recover all interrupted jobs."""
        return await self._recovery.recover_all()

    async def get_recovery_report(self) -> Dict[str, Any]:
        interrupted = await self._recovery.detect_interrupted()
        return {
            "interrupted_jobs": interrupted,
            "total": len(interrupted),
            "by_state": {},
        }

    # ---- Logging ----

    async def _log(self, job_id: str, level: str, message: str, extra: Optional[Dict[str, Any]] = None, step: Optional[str] = None) -> None:
        async with self._session()() as session:
            log = JobLogOrm(
                job_id=job_id,
                level=level,
                message=message,
                step=step,
                details=extra or {},
            )
            session.add(log)
            await session.commit()

    async def get_logs(self, job_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        async with self._session()() as session:
            result = await session.execute(
                select(JobLogOrm)
                .where(JobLogOrm.job_id == job_id)
                .order_by(JobLogOrm.timestamp.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
        return [
            {
                "level": r.level,
                "message": r.message,
                "step": r.step,
                "timestamp": r.timestamp.isoformat(),
                "details": r.details,
            }
            for r in reversed(rows)
        ]

    # ---- Execution ----

    async def execute_job(self, job: IntelligenceJob) -> Dict[str, Any]:
        """Full execution pipeline for a single job:

        intent → memory → reality graph → reasoning → planning → critique →
        routing → execution → artifact → provenance
        """
        await self.set_state(job.id, JobState.PLANNING, progress=0.0)

        # Step 1: Intent (parse if not already)
        intent_result: IntentResult
        if job.intent:
            intent = __import__("app.intelligence.schemas", fromlist=["Intent"]).Intent(**job.intent)
            intent_result = IntentResult(intent=intent)
        else:
            intent_result = await self._intent_engine.parse(job.request, job.inputs)
            job.intent = intent_result.intent.model_dump()
            async with self._session()() as session:
                j = await session.get(IntelligenceJob, job.id)
                if j:
                    j.intent = intent_result.intent.model_dump()
                    await session.commit()
        await self._log(job.id, "INFO", f"Intent parsed: {intent_result.intent.category.value}")

        await self._decision_trace.record(
            step="intent",
            decision=f"Parsed intent as {intent_result.intent.category.value}",
            reasoning=str(intent_result.alternative_interpretations),
            job_id=job.id,
        )

        # Step 2: Reasoning → Plan
        await self.set_state(job.id, JobState.PLANNING, progress=0.2)
        reasoning_result = await self._reasoning.reason(job.request, job.inputs)
        plan: Plan = reasoning_result["plan"]
        await self.update_plan(job.id, plan)
        await self._log(job.id, "INFO", f"Plan generated with {len(plan.steps)} steps")

        # Step 3: Self-Critique → Revision → Validation
        critique_result = await self._self_critique.critique_plan(plan, intent_result.intent)
        if critique_result.revised_plan:
            plan = critique_result.revised_plan
            await self.update_plan(job.id, plan)
            await self._log(job.id, "INFO", f"Plan revised: {len(critique_result.issues)} issues found")
            await self._decision_trace.record(
                step="critique",
                decision="Plan revised based on critique",
                reasoning=f"{len(critique_result.issues)} issues, {len([i for i in critique_result.issues if i['severity'] == 'error'])} errors",
                job_id=job.id,
                details={"issues": critique_result.issues},
            )

        # Step 4: Consistency check
        report = self._reasoning.consistency_engine.check(plan)
        if self._reasoning.consistency_engine.is_blocking_error(report):
            await self.set_state(
                job.id, JobState.FAILED,
                error=f"Consistency check failed: {len(report.diagnostics)} errors",
            )
            await self._log(job.id, "ERROR", "Plan failed consistency check", extra={"diagnostics": [d.model_dump() for d in report.diagnostics]})
            return {"job_id": job.id, "status": "failed", "reason": "consistency_check_failed"}

        await self.set_state(job.id, JobState.RUNNING, progress=0.3)

        # Step 5: Routing
        routing = await self._tool_router.route(
            intent_result.intent,
            plan.steps[1] if len(plan.steps) > 1 else None,
        )
        await self._log(job.id, "INFO", f"Routed to: {routing.tool.value} ({routing.selected_model})")

        job.selected_tool = routing.tool.value
        job.selected_model = routing.selected_model
        async with self._session()() as session:
            j = await session.get(IntelligenceJob, job.id)
            if j:
                j.selected_tool = routing.tool.value
                j.selected_model = routing.selected_model
                await session.commit()

        # Step 6: Execute plan steps + check for completion
        await self.set_state(job.id, JobState.CHECKPOINTED, progress=0.4)

        runner = JobRunner(
            job_id=job.id,
            checkpoint_mgr=self._checkpoints,
            artifact_mgr=self._artifacts,
            decision_trace=self._decision_trace,
            tool_router=self._tool_router,
            log_fn=lambda level, msg, **kw: asyncio.create_task(self._log(job.id, level, msg, extra=kw)),
        )
        self._running[job.id] = runner

        total_steps = len(plan.steps)
        completed_steps: List[str] = []
        step_results: List[Dict[str, Any]] = []
        resumable_state = job.resumable_state or {}

        # Resume from checkpoint if available
        resume_from = 0
        if resumable_state:
            completed_steps = resumable_state.get("completed_steps", [])
            resume_from = len(completed_steps)

        for i, step in enumerate(plan.steps[resume_from:], start=resume_from):
            if runner.is_cancelled:
                await self.set_state(job.id, JobState.CANCELLED, failure_state=JobFailureState.CANCELLED)
                return {"job_id": job.id, "status": "cancelled"}

            result = await runner.run_step(plan, i, resumable_state)
            step_results.append(result)
            completed_steps.append(step.id)

            progress = 0.4 + (0.5 * (i + 1) / total_steps)
            await self.update_progress(job.id, min(progress, 0.95), step=step.id, state=JobState.RUNNING)

            # Create checkpoint after each step
            await self._checkpoints.create_checkpoint(
                job_id=job.id,
                step_id=step.id,
                state={
                    "plan_step_index": i,
                    "plan": plan.model_dump(),
                    "step_result": result["result"],
                },
                progress=progress,
                completed_steps=completed_steps,
                notes=f"Completed step: {step.description}",
            )

        # Step 7: Produce artifact
        await self.set_state(job.id, JobState.RUNNING, progress=0.9)

        content_digest = ""
        if step_results:
            raw = json.dumps(step_results, sort_keys=True, default=str).encode()
            content_digest = self._artifacts.compute_digest(raw)

        artifact = await self._artifacts.register_artifact(
            job_id=job.id,
            type=job.intent_category or "general",
            path=f"artifacts/{job.id}/result.json",
            model_version=routing.selected_model,
            input_digest=content_digest,
            configuration={
                "plan": plan.model_dump(),
                "routing": routing.model_dump(),
                "intent": intent_result.intent.model_dump(),
            },
            execution_state={
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "step_results": step_results,
                "routing_decision": routing.model_dump(),
            },
            provenance={
                "job_id": job.id,
                "model_version": routing.selected_model,
                "timestamp": datetime.utcnow().isoformat(),
                "plan_id": plan.id,
            },
        )

        # Step 8: Finalize
        async with self._session()() as session:
            j = await session.get(IntelligenceJob, job.id)
            if j:
                j.state = JobState.COMPLETED
                j.plan_status = PlanStatus.EXECUTABLE
                j.progress = 1.0
                j.result = {
                    "artifacts": [artifact.model_dump()],
                    "step_count": total_steps,
                    "completed_steps": len(completed_steps),
                    "routing": routing.model_dump(),
                    "plan": plan.model_dump(),
                }
                j.execution_log = {"steps": step_results, "completed": True}
                j.completed_at = datetime.utcnow()
                await session.commit()

        await self._log(job.id, "INFO", "Job completed successfully")
        await self._decision_trace.record(
            step="completion",
            decision="Job completed",
            reasoning=f"Executed {total_steps} steps, produced {len(step_results)} artifacts",
            job_id=job.id,
        )
        del self._running[job.id]

        return {
            "job_id": job.id,
            "status": "completed",
            "artifacts": [artifact.model_dump()],
            "step_count": total_steps,
        }

    # ---- Orchestration loop ----

    async def start(self, poll_interval: float = 1.0) -> None:
        """Main processing loop. Recovers interrupted jobs and processes queue."""
        await self.recover_interrupted()
        self._running_flag = True
        while self._running_flag:
            job = await self._scheduler.next_job()
            if job:
                await self._run_job_async(job)
            await asyncio.sleep(poll_interval)

    def _run_job_async(self, job: IntelligenceJob) -> asyncio.Task:
        if job.id in self._running_jobs:
            return self._running_jobs[job.id]
        task = asyncio.create_task(self._safe_execute(job))
        self._running_jobs[job.id] = task
        return task

    async def _safe_execute(self, job: IntelligenceJob) -> Dict[str, Any]:
        try:
            return await self.execute_job(job)
        except Exception as e:
            await self.set_state(
                job.id, JobState.RECOVERABLE,
                failure_state=JobFailureState.RECOVERABLE,
                error=str(e),
            )
            await self._log(job.id, "ERROR", f"Job execution error: {e}")
            return {"job_id": job.id, "status": "recoverable", "error": str(e)}

    async def stop(self) -> None:
        self._running_flag = False
        for task in self._running_jobs.values():
            task.cancel()
        self._running_jobs.clear()
        self._running.clear()

    @property
    def tool_router(self) -> ToolRouter:
        return self._tool_router

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoints

    @property
    def artifact_manager(self) -> ArtifactManager:
        return self._artifacts

    @property
    def scheduler(self) -> PriorityScheduler:
        return self._scheduler

    @property
    def recovery(self) -> FailureRecovery:
        return self._recovery

    @property
    def intent_engine(self) -> IntentEngine:
        return self._intent_engine

    @property
    def reasoning_engine(self) -> ReasoningEngine:
        return self._reasoning

    @property
    def decision_trace(self) -> DecisionTrace:
        return self._decision_trace

    @property
    def creative_director(self) -> CreativeDirector:
        return self._creative_director

    @property
    def visual_planner(self) -> VisualPlanningEngine:
        return self._visual_planner

    @property
    def self_critique(self) -> SelfCritiqueLoop:
        return self._self_critique
