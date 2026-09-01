from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.schemas import GenerationRequest, JobResponse
from app.models.models import Job, Asset, JobStatus
from app.services.orchestrator import JobOrchestrator
from app.services.storage import storage_service
from app.core.config import settings
from uuid import UUID

router = APIRouter()


def get_orchestrator() -> JobOrchestrator:
    from app.main import orchestrator
    return orchestrator


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def generate_video(
    request: GenerationRequest,
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
):
    provider = request.provider or settings.default_video_provider
    input_assets = []
    if request.input_asset_ids:
        for asset_id in request.input_asset_ids:
            asset = await db.get(Asset, str(asset_id))
            if asset:
                input_assets.append({"id": str(asset.id), "type": asset.asset_type, "url": asset.storage_url})

    job = Job(
        user_id=current_user.id,
        project_id=project_id,
        job_type=request.job_type,
        provider=provider,
        model=request.model,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        parameters=request.parameters or {},
        input_assets=input_assets,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
