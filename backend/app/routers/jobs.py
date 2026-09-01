from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Job, Asset, JobStatus, JobType
from app.schemas.schemas import JobResponse, GenerationRequest
from app.services.orchestrator import JobOrchestrator
from app.services.storage import storage_service
from app.core.config import settings
from uuid import UUID

router = APIRouter()


def get_orchestrator() -> JobOrchestrator:
    from app.main import orchestrator
    return orchestrator


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: GenerationRequest,
    project_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
):
    provider = job_data.provider or settings.default_video_provider
    input_assets = []
    if job_data.input_asset_ids:
        for asset_id in job_data.input_asset_ids:
            asset = await db.get(Asset, str(asset_id))
            if asset:
                input_assets.append({"id": str(asset.id), "type": asset.asset_type, "url": asset.storage_url})

    job = Job(
        user_id=current_user.id,
        project_id=project_id,
        job_type=job_data.job_type,
        provider=provider,
        model=job_data.model,
        prompt=job_data.prompt,
        negative_prompt=job_data.negative_prompt,
        parameters=job_data.parameters or {},
        input_assets=input_assets,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).where(Job.user_id == current_user.id)
    if project_id:
        query = query.where(Job.project_id == project_id)
    if status:
        query = query.where(Job.status == status)
    query = query.order_by(Job.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be cancelled")
    success = await orchestrator.cancel_job(job_id)
    return {"success": success}
