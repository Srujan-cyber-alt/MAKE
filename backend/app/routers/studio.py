from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User
from app.services.studio_orchestrator import StudioOrchestrator, CreationMode
from app.services.capability_registry import CapabilityRegistry
from app.services.real_time_progress import RealTimeProgress
import uuid

router = APIRouter()


@router.get("/projects/{project_id}")
async def get_studio_project(project_id: str, current_user: User = Depends(get_current_user)):
    return {
        "project_id": project_id,
        "user_id": current_user.id,
        "modes": [
            {"id": CreationMode.CREATE, "label": "Create", "icon": "Sparkles"},
            {"id": CreationMode.EDIT, "label": "Edit", "icon": "Scissors"},
            {"id": CreationMode.TRANSFORM, "label": "Transform", "icon": "RefreshCw"},
            {"id": CreationMode.ANIMATE, "label": "Animate", "icon": "PlayCircle"},
            {"id": CreationMode.EXTEND, "label": "Extend", "icon": "PlusCircle"},
            {"id": CreationMode.REMIX, "label": "Remix", "icon": "Copy"},
            {"id": CreationMode.AUTO, "label": "Auto", "icon": "Wand2"},
        ],
    }


@router.post("/projects/{project_id}/command")
async def execute_studio_command(
    project_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    command = request.get("command", "")
    mode = request.get("mode", CreationMode.AUTO)
    context = request.get("context", {})

    if not command.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Command is required")

    result = await StudioOrchestrator.route_command(
        command=command,
        project_id=project_id,
        user_id=current_user.id,
        mode=mode,
        context=context,
    )
    return result


@router.get("/projects/{project_id}/capabilities")
async def get_studio_capabilities(project_id: str, current_user: User = Depends(get_current_user)):
    capabilities = await CapabilityRegistry.get_all_capabilities()
    return capabilities


@router.get("/projects/{project_id}/progress/{job_id}")
async def get_studio_progress(project_id: str, job_id: str, current_user: User = Depends(get_current_user)):
    progress = await RealTimeProgress.get_progress(job_id)
    return progress


@router.get("/projects/{project_id}/assets")
async def get_studio_assets(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.models import Asset

    result = await db.execute(
        select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    return [
        {
            "id": asset.id,
            "filename": asset.filename,
            "asset_type": asset.asset_type.value if asset.asset_type else None,
            "status": asset.status.value if asset.status else None,
            "duration_seconds": asset.duration_seconds,
            "width": asset.width,
            "height": asset.height,
            "fps": asset.fps,
            "storage_url": asset.storage_url,
            "thumbnail_path": asset.thumbnail_path,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }
        for asset in assets
    ]
