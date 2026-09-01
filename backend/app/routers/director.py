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
    GeneratePlanRequest,
    GenerationJobResponse,
)
from app.services.director import director_service
from app.services.director_validator import DirectorPlanValidator, DirectorValidationError
from app.services.generation_engine import GenerationEngine
from app.models.models import User

router = APIRouter()


def get_generation_engine() -> GenerationEngine:
    from app.main import generation_engine
    return generation_engine


def _plan_to_response(plan) -> DirectorPlanResponse:
    characters = []
    products = []
    locations = []
    references = []
    for scene in plan.scenes:
        for shot in scene.shots:
            if shot.characters:
                characters.extend([c for c in shot.characters if c not in characters])
            if shot.products:
                products.extend([p for p in shot.products if p not in products])
            if shot.locations:
                locations.extend([l for l in shot.locations if l not in locations])
            if shot.references:
                references.extend([r for r in shot.references if r not in references])

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
        intent={
            "objective": plan.objective,
            "content_type": plan.content_type,
            "audience": plan.audience,
            "tone": plan.tone,
            "style": plan.style,
            "total_duration_seconds": plan.duration,
            "aspect_ratio": plan.aspect_ratio,
            "resolution": plan.resolution,
            "platform": plan.platform,
            "characters": characters,
            "products": products,
            "locations": locations,
            "references": references,
        },
    )


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

    return _plan_to_response(plan)


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
    return _plan_to_response(plan)


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
        _plan_to_response(p)
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
    return _plan_to_response(plan)


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
    return _plan_to_response(plan)


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
    return _plan_to_response(plan)


@router.post("/plans/{plan_id}/generate", response_model=list[GenerationJobResponse], status_code=status.HTTP_201_CREATED)
async def generate_plan(
    plan_id: str,
    request: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: GenerationEngine = Depends(get_generation_engine),
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
    jobs = await engine.execute_plan(
        plan=plan,
        user_id=current_user.id,
        shot_ids=request.shot_ids or None,
        scene_ids=request.scene_ids or None,
        preferences=request.preferences,
    )

    return [
        GenerationJobResponse(
            id=j.id,
            project_id=j.project_id,
            plan_id=j.parameters.get("plan_id") if j.parameters else None,
            scene_id=j.parameters.get("scene_id") if j.parameters else None,
            shot_id=j.parameters.get("shot_id") if j.parameters else None,
            job_type=j.job_type.value if hasattr(j.job_type, 'value') else str(j.job_type),
            status=j.status.value if hasattr(j.status, 'value') else str(j.status),
            provider=j.provider,
            model=j.model,
            prompt=j.prompt,
            parameters=j.parameters,
            result=j.result,
            error=j.error,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]
