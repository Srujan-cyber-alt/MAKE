from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.core.auth import get_current_user
from app.schemas.schemas import GenerationRequest
from app.routers.jobs import create_job

router = APIRouter()


@router.post("")
async def generate_video(
    request: GenerationRequest,
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    return await create_job(request, project_id=project_id, current_user=current_user)
