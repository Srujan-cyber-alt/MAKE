"""FastAPI router for the MAKE Intelligence Core."""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.intelligence.schemas import (
    JobCreate, JobState, ExecutionRequest, ExecutionResult,
    IntentResult, Plan, EntityType, RelationType,
)
from app.intelligence.jobs.job_manager import JobManager


router = APIRouter()

_jm: JobManager = JobManager()


class CreateJobRequest(BaseModel):
    request: str
    intent_category: Optional[str] = None
    priority: int = 0
    inputs: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: float = 300.0
    parent_job_id: Optional[str] = None
    requires_approval: bool = False


class MemoryEntityRequest(BaseModel):
    entity_type: str
    name: str
    attributes: Optional[Dict[str, Any]] = None
    scope: str = "default"
    consent: bool = True


class RelationRequest(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    attributes: Optional[Dict[str, Any]] = None


class GraphNodeRequest(BaseModel):
    name: str
    entity_type: str
    attributes: Optional[Dict[str, Any]] = None


class GraphEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    relation_type: str
    weight: float = 1.0
    attributes: Optional[Dict[str, Any]] = None


class IntentRequest(BaseModel):
    request: str
    context: Optional[Dict[str, Any]] = None


class CreativeRequest(BaseModel):
    prompt: str
    constraints: Optional[Dict[str, Any]] = None


class ContextRequest(BaseModel):
    key: str
    data: Dict[str, Any]
    scope: str = "default"
    auto_approve: bool = False


# ---------------------------------------------------------------------------
# Tool Router (registered before /{job_id} so the static /tools path is not
# swallowed by the dynamic path-parameter route)
# ---------------------------------------------------------------------------


@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools():
    adapters = _jm.tool_router.list_adapters()
    return [
        {"name": a.name, "tool_type": a.tool_type.value, "capabilities": a.get_capabilities()}
        for a in adapters
    ]


@router.post("/tools/execute", response_model=Dict[str, Any])
async def execute_tool(req: ExecutionRequest):
    result = await _jm.tool_router.execute(req)
    return result.model_dump()


@router.post("/tools/route", response_model=Dict[str, Any])
async def route_request(req: ExecutionRequest):
    decision = await _jm.tool_router.route_request(req)
    return decision.model_dump()


@router.get("/tools/health", response_model=Dict[str, Any])
async def tools_health():
    return await _jm.tool_router.check_all_health()


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_job(req: CreateJobRequest):
    spec = JobCreate(**req.model_dump())
    job = await _jm.create_job(spec)
    return {"job_id": job.id, "state": job.state.value, "created_at": job.created_at.isoformat()}


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_jobs(
    state: Optional[JobState] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
):
    jobs = await _jm.list_jobs(state=state, user_id=user_id, project_id=project_id, limit=limit)
    return [
        {"job_id": j.id, "state": j.state.value, "progress": j.progress,
         "created_at": j.created_at.isoformat(), "updated_at": j.updated_at.isoformat(),
         "request": j.request, "error": j.error, "retry_count": j.retry_count}
        for j in jobs
    ]


@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job(job_id: str):
    job = await _jm.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    checkpoints = await _jm.checkpoint_manager.list_checkpoints(job_id)
    logs = await _jm.get_logs(job_id)
    plan = Plan(**job.plan) if job.plan else None
    return {
        "job_id": job.id,
        "state": job.state.value,
        "failure_state": job.failure_state.value if job.failure_state else None,
        "progress": job.progress,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "inputs": job.inputs,
        "result": job.result,
        "error": job.error,
        "selected_tool": job.selected_tool,
        "selected_model": job.selected_model,
        "plan": plan.model_dump() if plan else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "resumable_state": job.resumable_state,
        "checkpoints": checkpoints,
        "logs": logs,
    }


@router.post("/{job_id}/cancel", response_model=Dict[str, Any])
async def cancel_job(job_id: str):
    success = await _jm.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"job_id": job_id, "state": "cancelled"}


@router.post("/{job_id}/pause", response_model=Dict[str, Any])
async def pause_job(job_id: str, reason: str = ""):
    success = await _jm.pause_job(job_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not pausable")
    return {"job_id": job_id, "state": "paused"}


@router.post("/{job_id}/resume", response_model=Dict[str, Any])
async def resume_job(job_id: str):
    success = await _jm.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not resumable")
    return {"job_id": job_id, "state": "queued"}


@router.post("/{job_id}/run", response_model=Dict[str, Any])
async def run_job(job_id: str):
    job = await _jm.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.state not in (JobState.QUEUED, JobState.RECOVERABLE, JobState.PAUSED):
        raise HTTPException(status_code=400, detail=f"Job in state {job.state.value} cannot be run")
    result = await _jm.execute_job(job)
    return result


# ---------------------------------------------------------------------------
# Recovery endpoints
# ---------------------------------------------------------------------------


@router.get("/recovery/interrupted", response_model=List[Dict[str, Any]])
async def get_interrupted_jobs():
    return await _jm.recovery.detect_interrupted()


@router.post("/recovery/recover", response_model=List[Dict[str, Any]])
async def recover_all_jobs():
    return await _jm.recover_interrupted()


@router.post("/recovery/recover/{job_id}", response_model=Dict[str, Any])
async def recover_job(job_id: str):
    result = await _jm.recovery.recover_job(job_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return result


# ---------------------------------------------------------------------------
# Intent parsing & planning
# ---------------------------------------------------------------------------


@router.post("/intent", response_model=Dict[str, Any])
async def parse_intent(req: IntentRequest):
    result = await _jm.intent_engine.parse(req.request, req.context)
    return result.intent.model_dump()


@router.post("/plan", response_model=Dict[str, Any])
async def generate_plan(req: IntentRequest):
    result = await _jm.reasoning_engine.reason(req.request, req.context)
    plan = result["plan"]
    report = result["consistency_report"]
    return {
        "plan": plan.model_dump(),
        "consistency_report": {
            "plan_id": report.plan_id,
            "passed": report.passed,
            "diagnostics": [d.model_dump() for d in report.diagnostics],
        },
        "clarity": result["clarity"],
    }


@router.post("/plan/critique", response_model=Dict[str, Any])
async def critique_plan(plan_data: Dict[str, Any]):
    plan = Plan(**plan_data)
    result = await _jm.self_critique.critique_plan(plan)
    return {
        "issues": result.issues,
        "was_revised": result.was_revised,
        "revised_plan": result.revised_plan.model_dump() if result.revised_plan else None,
    }


# ---------------------------------------------------------------------------
# Creative Director
# ---------------------------------------------------------------------------


@router.post("/creative/direct", response_model=Dict[str, Any])
async def creative_direct(req: CreativeRequest):
    decision = _jm.creative_director.plan(req.prompt, constraints=req.constraints)
    return decision.model_dump()


@router.post("/creative/visual-plan", response_model=Dict[str, Any])
async def visual_plan(req: CreativeRequest):
    decision = _jm.creative_director.plan(req.prompt, constraints=req.constraints)
    plan = _jm.visual_planner.plan_visual(req.prompt, decision)
    return plan.model_dump()


# ---------------------------------------------------------------------------
# World Memory
# ---------------------------------------------------------------------------


@router.post("/memory/entity", response_model=Dict[str, Any])
async def create_memory_entity(req: MemoryEntityRequest):
    entity_type = EntityType(req.entity_type)
    try:
        record = await _jm.world_memory.store_entity(
            entity_type=entity_type,
            name=req.name,
            attributes=req.attributes or {},
            scope=req.scope,
            consent=req.consent,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    return record.model_dump()


@router.get("/memory/entities", response_model=List[Dict[str, Any]])
async def list_entities(
    entity_type: Optional[str] = None,
    name: Optional[str] = None,
    scope: str = "default",
):
    etype = EntityType(entity_type) if entity_type else None
    entities = await _jm.world_memory.find_entities(entity_type=etype, name=name, scope=scope)
    return [e.model_dump() for e in entities]


@router.post("/memory/relation", response_model=Dict[str, Any])
async def create_relation(req: RelationRequest):
    rel_type = RelationType(req.relation_type)
    rid = await _jm.world_memory.add_relation(
        req.source_id, req.target_id, rel_type, req.weight, req.attributes or {}
    )
    return {"id": rid, "source_id": req.source_id, "target_id": req.target_id, "relation_type": req.relation_type}


@router.get("/memory/related/{entity_id}", response_model=List[Dict[str, Any]])
async def get_related(entity_id: str):
    return await _jm.world_memory.get_related(entity_id)


# ---------------------------------------------------------------------------
# Reality Graph
# ---------------------------------------------------------------------------


@router.post("/graph/node", response_model=Dict[str, Any])
async def create_node(req: GraphNodeRequest):
    record = await _jm.reality_graph.add_node(req.name, req.entity_type, req.attributes or {})
    return record.model_dump()


@router.post("/graph/edge", response_model=Dict[str, Any])
async def create_edge(req: GraphEdgeRequest):
    record = await _jm.reality_graph.add_edge(
        req.source_node_id, req.target_node_id, req.relation_type, req.weight, req.attributes or {}
    )
    return record.model_dump()


@router.get("/graph/neighbors/{node_id}", response_model=List[Dict[str, Any]])
async def get_graph_neighbors(node_id: str):
    neighbors = await _jm.reality_graph.get_neighbors(node_id)
    return [n.model_dump() for n in neighbors]


@router.get("/graph/traverse/{node_id}", response_model=List[Dict[str, Any]])
async def traverse_graph(node_id: str, max_depth: int = 3):
    return await _jm.reality_graph.traverse(node_id, max_depth=max_depth)


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


@router.get("/artifacts/job/{job_id}", response_model=List[Dict[str, Any]])
async def get_job_artifacts(job_id: str):
    artifacts = await _jm.artifact_manager.get_artifacts_for_job(job_id)
    return [a.model_dump() for a in artifacts]


@router.get("/artifacts/{artifact_id}/provenance", response_model=Dict[str, Any])
async def get_artifact_provenance(artifact_id: str):
    provenance = await _jm.artifact_manager.get_artifact_provenance(artifact_id)
    if provenance is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return provenance


# ---------------------------------------------------------------------------
# Personal Context
# ---------------------------------------------------------------------------


@router.post("/context", response_model=Dict[str, Any])
async def store_context(req: ContextRequest):
    record = await _jm.personal_context.store_context(
        key=req.key, data=req.data, scope=req.scope, auto_approve=req.auto_approve
    )
    return record.model_dump()


@router.post("/context/{entry_id}/approve", response_model=Dict[str, Any])
async def approve_context(entry_id: str, approved_by: str = "user"):
    record = await _jm.personal_context.approve_context(entry_id, approved_by)
    if record is None:
        raise HTTPException(status_code=404, detail="Context entry not found")
    return record.model_dump()


@router.get("/context/approved", response_model=List[Dict[str, Any]])
async def get_approved_context(scope: str = "default"):
    records = await _jm.personal_context.get_approved(scope=scope)
    return [r.model_dump() for r in records]


@router.get("/context/pending", response_model=List[Dict[str, Any]])
async def get_pending_context(scope: str = "default"):
    records = await _jm.personal_context.get_pending(scope=scope)
    return [r.model_dump() for r in records]


# ---------------------------------------------------------------------------
# Decision trace
# ---------------------------------------------------------------------------


@router.get("/decisions/{job_id}", response_model=List[Dict[str, Any]])
async def get_job_decisions(job_id: str):
    records = await _jm.decision_trace.get_for_job(job_id)
    return [r.model_dump() for r in records]


# ---------------------------------------------------------------------------
# Scheduler status
# ---------------------------------------------------------------------------


@router.get("/scheduler/status", response_model=Dict[str, Any])
async def scheduler_status():
    return _jm.scheduler.schedule_summary()
