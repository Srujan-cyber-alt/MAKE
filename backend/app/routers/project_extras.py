from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, ProjectVersion, ReferenceAsset
from app.schemas.schemas import ProjectVersionResponse, ProjectContextUpdate, ProjectContextResponse, ReferenceAssetCreate, ReferenceAssetResponse

router = APIRouter()


@router.post("/{project_id}/versions", response_model=ProjectVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    count_result = await db.execute(
        select(func.count(ProjectVersion.id)).where(ProjectVersion.project_id == project_id)
    )
    version_number = count_result.scalar_one() + 1

    snapshot = {
        "project_id": str(project.id),
        "name": project.name,
        "description": project.description,
        "settings": project.settings,
        "metadata": project.project_metadata,
        "created_at": project.created_at.isoformat(),
    }

    version = ProjectVersion(
        project_id=project_id,
        version_number=version_number,
        name=name,
        description=description,
        snapshot=snapshot,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{project_id}/versions", response_model=list[ProjectVersionResponse])
async def list_versions(
    project_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.project_id == project_id).order_by(ProjectVersion.version_number.desc())
    )
    return result.scalars().all()


@router.get("/versions/{version_id}", response_model=ProjectVersionResponse)
async def get_version(
    version_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


@router.post("/versions/{version_id}/restore")
async def restore_version(
    version_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    project = await db.get(Project, str(version.project_id))
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    snapshot = version.snapshot
    project.name = snapshot.get("name", project.name)
    project.description = snapshot.get("description", project.description)
    project.settings = snapshot.get("settings", project.settings)
    project.project_metadata = snapshot.get("metadata", project.project_metadata)
    await db.commit()
    return {"status": "restored", "version": version.version_number}


@router.get("/{project_id}/context", response_model=ProjectContextResponse)
async def get_project_context(
    project_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    context = project.project_metadata.get("context", {}) if project.project_metadata else {}
    return ProjectContextResponse(project_id=project.id, context=context)


@router.post("/{project_id}/context", response_model=ProjectContextResponse)
async def update_project_context(
    project_id: str,
    context_data: ProjectContextUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project.project_metadata:
        project.project_metadata = {}
    project.project_metadata["context"] = context_data.context
    await db.commit()
    await db.refresh(project)
    return ProjectContextResponse(project_id=project.id, context=context_data.context)


@router.post("/{project_id}/references", response_model=ReferenceAssetResponse, status_code=status.HTTP_201_CREATED)
async def add_reference(
    project_id: str,
    ref_data: ReferenceAssetCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    asset = await db.get(Asset, str(ref_data.asset_id))
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found in project")

    ref = ReferenceAsset(
        project_id=project_id,
        asset_id=ref_data.asset_id,
        role=ref_data.role,
        metadata=ref_data.metadata,
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    return ref


@router.get("/{project_id}/references", response_model=list[ReferenceAssetResponse])
async def list_references(
    project_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await db.execute(
        select(ReferenceAsset).where(ReferenceAsset.project_id == project_id).order_by(ReferenceAsset.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/references/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    ref_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReferenceAsset).where(ReferenceAsset.id == ref_id)
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    await db.delete(ref)
    await db.commit()
