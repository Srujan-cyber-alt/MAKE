from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, Asset, AssetStatus
from app.schemas.schemas import AssetResponse

router = APIRouter()


@router.post("/{project_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: str = "reference",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from app.services.storage import storage_service
    storage_path, file_size = await storage_service.upload_file(
        file.file, file.filename or "upload", project_id, content_type=file.content_type
    )

    asset = Asset(
        project_id=project_id,
        asset_type=asset_type,
        filename=file.filename or "upload",
        content_type=file.content_type,
        file_size=file_size,
        storage_path=storage_path,
        storage_url=storage_service.get_file_url(storage_path),
        status=AssetStatus.READY,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/{project_id}/assets", response_model=list[AssetResponse])
async def list_project_assets(
    project_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await db.execute(select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc()))
    return result.scalars().all()
