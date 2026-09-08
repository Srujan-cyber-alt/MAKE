"""
MAKE Autonomous Agent Core V2 — API Routes.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import time
import uuid

from app.intelligence.jobs.job_manager import JobManager, JobStatus
from app.intelligence.core.event_stream import EventType
from app.schemas.intelligence_v2 import (
    CreateJobRequest,
    JobResponse,
    ExecutionGraphResponse,
    ArtifactResponse,
    EventResponse,
    ProjectStateResponse,
)
from app.core.auth import get_current_user

router = APIRouter()

_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


@router.post("/jobs", response_model=JobResponse)
async def create_job(request: CreateJobRequest, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    job = manager.create_job(
        intent=request.intent,
        project_id=request.project_id,
        user_id=current_user.get("user_id") if isinstance(current_user, dict) else None,
        max_iterations=request.max_iterations,
        metadata=request.metadata,
        idempotency_key=request.idempotency_key,
        owner=request.owner or (current_user.get("email") if isinstance(current_user, dict) else None),
    )
    return JobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        user_id=job.user_id,
        intent=job.intent,
        status=JobStatusSchema(job.status.value),
        iterations=job.iterations,
        max_iterations=job.max_iterations,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        owner=job.owner,
        metadata=job.metadata,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    job = manager.get_job(UUID(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        user_id=job.user_id,
        intent=job.intent,
        status=JobStatusSchema(job.status.value),
        iterations=job.iterations,
        max_iterations=job.max_iterations,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        owner=job.owner,
        metadata=job.metadata,
    )


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    graph = manager.resume_from_checkpoint(UUID(job_id))
    if not graph:
        raise HTTPException(status_code=404, detail="Job or checkpoint not found")
    return {"status": "resumed", "execution_id": str(graph.execution_id)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    job = manager.cancel_job(UUID(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "cancelled", "job_id": job_id}


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    job = manager.get_job(UUID(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job.status.value,
        "iterations": job.iterations,
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/jobs/{job_id}/events", response_model=List[EventResponse])
async def get_job_events(job_id: str, after_sequence: int = Query(0), current_user=Depends(get_current_user)):
    manager = get_job_manager()
    events = manager.get_events(UUID(job_id), after_sequence)
    return [EventResponse(**e) for e in events]


@router.get("/jobs/{job_id}/artifacts", response_model=List[ArtifactResponse])
async def get_job_artifacts(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    artifacts = manager.get_artifacts(UUID(job_id))
    return [ArtifactResponse(**a) for a in artifacts]


@router.get("/jobs/{job_id}/trace")
async def get_job_trace(job_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    job = manager.get_job(UUID(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "intent": job.intent,
        "status": job.status.value,
        "events": job.events,
        "artifacts": job.artifacts,
    }


@router.get("/projects/{project_id}/state", response_model=ProjectStateResponse)
async def get_project_state(project_id: str, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    state = manager.project_memory.get_project(UUID(project_id))
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectStateResponse(
        project_id=state.project_id,
        entities={k: v.to_dict() for k, v in state.entities.items()},
        versions=[v.to_dict() for v in state.versions],
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(owner: Optional[str] = None, current_user=Depends(get_current_user)):
    manager = get_job_manager()
    jobs = manager.list_jobs(owner=owner)
    return [
        JobResponse(
            job_id=job.job_id,
            project_id=job.project_id,
            user_id=job.user_id,
            intent=job.intent,
            status=JobStatusSchema(job.status.value),
            iterations=job.iterations,
            max_iterations=job.max_iterations,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            owner=job.owner,
            metadata=job.metadata,
        )
        for job in jobs
    ]
