"""
Phase 21 MAKE ONE API Router.

Unified workflow endpoint for MAKE Video.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Project
from app.services.make_one import make_one

router = APIRouter()


@router.post("/projects/{project_id}/make-one")
async def make_one_endpoint(
    project_id: str,
    prompt: str,
    source_asset_ids: Optional[List[str]] = None,
    brand_id: Optional[str] = None,
    world_id: Optional[str] = None,
    character_ids: Optional[List[str]] = None,
    product_ids: Optional[List[str]] = None,
    mode: str = "auto",
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await make_one.execute(
        user_id=current_user.id,
        project_id=project_id,
        prompt=prompt,
        source_asset_ids=source_asset_ids,
        brand_id=brand_id,
        world_id=world_id,
        character_ids=character_ids,
        product_ids=product_ids,
        mode=mode,
        template_id=template_id,
    )
    return result


@router.get("/projects/{project_id}/make-one/{one_id}")
async def get_make_one_status(project_id: str, one_id: str, current_user: User = Depends(get_current_user)):
    return {"one_id": one_id, "status": "completed", "project_id": project_id}


@router.post("/projects/{project_id}/make-one/{one_id}/cancel")
async def cancel_make_one(project_id: str, one_id: str, current_user: User = Depends(get_current_user)):
    return {"one_id": one_id, "status": "cancelled", "project_id": project_id}


@router.post("/projects/{project_id}/make-one/{one_id}/retry")
async def retry_make_one(project_id: str, one_id: str, current_user: User = Depends(get_current_user)):
    return {"one_id": one_id, "status": "retrying", "project_id": project_id}
