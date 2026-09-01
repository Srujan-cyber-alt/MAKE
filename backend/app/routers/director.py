from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, DirectorPlan as DirectorPlanModel
from app.schemas.director import (
    DirectorRequest,
    DirectorPlanResponse,
    DirectorPlanCreate,
    DirectorPlanUpdate,
)
from app.services.director import director_service
from app.services.director_validator import DirectorPlanValidator, DirectorValidationError
from app.models.models import User

router = APIRouter()


@router.post("/plan", response_model=DirectorPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: DirectorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.project_id:
        project = await db.get(Project, request.project_id)
        if not project or project.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        project_id = request.project_id
    else:
        project = Project(
            user_id=current_user.id,
            name=f"Director Plan {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        project_id = project.id

    plan = await director_service.create_plan(request, project_id)
    errors = DirectorPlanValidator.validate(plan)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})

    await director_service.save_plan(plan)

    return DirectorPlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        creative_concept=plan.creative_concept,
        objective=plan.objective,
        content_type=plan.content_type,
        audience=plan.audience,
        tone=plan.tone,
        style=plan.style,
        duration=plan.duration,
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        platform=plan.platform,
        scenes=[s.model_dump() for s in plan.scenes],
        asset_requirements=[a.model_dump() for a in plan.asset_requirements],
        continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
        audio_requirements=[a.model_dump() for a in plan.audio_requirements],
        export_requirements=plan.export_requirements.model_dump(),
        generation_requirements=[g.model_dump() for g in plan.generation_requirements],
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/plans/{plan_id}", response_model=DirectorPlanResponse)
async def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    plan = director_service._model_to_plan(db_plan)
    return DirectorPlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        creative_concept=plan.creative_concept,
        objective=plan.objective,
        content_type=plan.content_type,
        audience=plan.audience,
        tone=plan.tone,
        style=plan.style,
        duration=plan.duration,
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        platform=plan.platform,
        scenes=[s.model_dump() for s in plan.scenes],
        asset_requirements=[a.model_dump() for a in plan.asset_requirements],
        continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
        audio_requirements=[a.model_dump() for a in plan.audio_requirements],
        export_requirements=plan.export_requirements.model_dump(),
        generation_requirements=[g.model_dump() for g in plan.generation_requirements],
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/projects/{project_id}/plans", response_model=list[DirectorPlanResponse])
async def list_plans(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    plans = await director_service.list_plans(project_id)
    return [
        DirectorPlanResponse(
            id=p.id,
            project_id=p.project_id,
            title=p.title,
            creative_concept=p.creative_concept,
            objective=p.objective,
            content_type=p.content_type,
            audience=p.audience,
            tone=p.tone,
            style=p.style,
            duration=p.duration,
            aspect_ratio=p.aspect_ratio,
            resolution=p.resolution,
            platform=p.platform,
            scenes=[s.model_dump() for s in p.scenes],
            asset_requirements=[a.model_dump() for a in p.asset_requirements],
            continuity_requirements=[c.model_dump() for c in p.continuity_requirements],
            audio_requirements=[a.model_dump() for a in p.audio_requirements],
            export_requirements=p.export_requirements.model_dump(),
            generation_requirements=[g.model_dump() for g in p.generation_requirements],
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in plans
    ]


@router.post("/plans/{plan_id}/approve", response_model=DirectorPlanResponse)
async def approve_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db_plan.status = "approved"
    await db.commit()
    await db.refresh(db_plan)

    plan = director_service._model_to_plan(db_plan)
    return DirectorPlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        creative_concept=plan.creative_concept,
        objective=plan.objective,
        content_type=plan.content_type,
        audience=plan.audience,
        tone=plan.tone,
        style=plan.style,
        duration=plan.duration,
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        platform=plan.platform,
        scenes=[s.model_dump() for s in plan.scenes],
        asset_requirements=[a.model_dump() for a in plan.asset_requirements],
        continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
        audio_requirements=[a.model_dump() for a in plan.audio_requirements],
        export_requirements=plan.export_requirements.model_dump(),
        generation_requirements=[g.model_dump() for g in plan.generation_requirements],
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/plans/{plan_id}/reject", response_model=DirectorPlanResponse)
async def reject_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db_plan.status = "rejected"
    await db.commit()
    await db.refresh(db_plan)

    plan = director_service._model_to_plan(db_plan)
    return DirectorPlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        creative_concept=plan.creative_concept,
        objective=plan.objective,
        content_type=plan.content_type,
        audience=plan.audience,
        tone=plan.tone,
        style=plan.style,
        duration=plan.duration,
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        platform=plan.platform,
        scenes=[s.model_dump() for s in plan.scenes],
        asset_requirements=[a.model_dump() for a in plan.asset_requirements],
        continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
        audio_requirements=[a.model_dump() for a in plan.audio_requirements],
        export_requirements=plan.export_requirements.model_dump(),
        generation_requirements=[g.model_dump() for g in plan.generation_requirements],
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/plans/{plan_id}/validate")
async def validate_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    plan = director_service._model_to_plan(db_plan)
    errors = DirectorPlanValidator.validate(plan)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@router.patch("/plans/{plan_id}", response_model=DirectorPlanResponse)
async def update_plan(
    plan_id: str,
    updates: DirectorPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if db_plan.status in ("approved", "executing", "completed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify plan in current status")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "duration" and value is not None:
            db_plan.intent["total_duration_seconds"] = value
        elif field == "aspect_ratio" and value is not None:
            db_plan.intent["aspect_ratio"] = value
        elif field == "style" and value is not None:
            db_plan.intent["style"] = value
        elif field == "status" and value is not None:
            db_plan.status = value
        elif hasattr(db_plan, field):
            setattr(db_plan, field, value)

    await db.commit()
    await db.refresh(db_plan)

    plan = director_service._model_to_plan(db_plan)
    return DirectorPlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        creative_concept=plan.creative_concept,
        objective=plan.objective,
        content_type=plan.content_type,
        audience=plan.audience,
        tone=plan.tone,
        style=plan.style,
        duration=plan.duration,
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        platform=plan.platform,
        scenes=[s.model_dump() for s in plan.scenes],
        asset_requirements=[a.model_dump() for a in plan.asset_requirements],
        continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
        audio_requirements=[a.model_dump() for a in plan.audio_requirements],
        export_requirements=plan.export_requirements.model_dump(),
        generation_requirements=[g.model_dump() for g in plan.generation_requirements],
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )
