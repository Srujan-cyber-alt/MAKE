from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.schemas import GenerationRequest, JobResponse
from app.schemas.director import GeneratePlanRequest, ModelSelectionResponse, GenerationJobResponse, BatchGenerateRequest, GenerationStatusResponse
from app.models.models import Job, Asset, JobStatus, Project, DirectorPlan as DirectorPlanModel
from app.services.orchestrator import JobOrchestrator
from app.services.storage import storage_service
from app.services.model_router import ModelRouter
from app.services.generation_engine import GenerationEngine
from app.services.prompt_compiler import PromptCompiler
from app.services.provider_health import provider_health_service
from app.core.config import settings
from app.providers.registry import get_provider_registry

router = APIRouter()


def get_orchestrator() -> JobOrchestrator:
    from app.main import orchestrator
    return orchestrator


def get_generation_engine() -> GenerationEngine:
    from app.main import generation_engine
    return generation_engine


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


@router.post("/model-select", response_model=ModelSelectionResponse)
async def select_model(
    request: GenerationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.director import GenerationRequirement, ShotPlan, CameraRequirement

    generation_req = GenerationRequirement(
        id="req-1",
        method=request.job_type.value if hasattr(request.job_type, 'value') else str(request.job_type),
        provider=request.provider,
        model=request.model,
        required_capabilities=[],
        parameters=request.parameters or {},
    )

    shot = ShotPlan(
        id="shot-1",
        scene_id="scene-1",
        order=0,
        description=request.prompt or "",
        subject=None,
        action=None,
        environment=None,
        camera=CameraRequirement(),
        lighting=None,
        composition=None,
        style=None,
        motion=None,
        duration_seconds=request.duration_seconds or 5.0,
        references=[],
        characters=[],
        products=[],
        locations=[],
        audio=[],
        continuity=[],
        generation=generation_req,
        status="planned",
    )

    registry = get_provider_registry()
    router = ModelRouter(registry)
    selection = await router.route(generation_req, shot, {})

    return ModelSelectionResponse(
        provider_id=selection.provider_id,
        model_id=selection.model_id,
        score=selection.score,
        reasons=selection.reasons,
        estimated_cost=selection.estimated_cost,
        estimated_duration=selection.estimated_duration,
        capabilities=selection.capabilities,
        fallback_models=selection.fallback_models,
    )


@router.post("/plan/generate", response_model=List[GenerationJobResponse], status_code=status.HTTP_201_CREATED)
async def generate_from_plan(
    request: GeneratePlanRequest,
    plan_id: str = Query(...),
    current_user=Depends(get_current_user),
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

    from app.services.director import director_service
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


@router.post("/batch/generate", response_model=List[GenerationJobResponse], status_code=status.HTTP_201_CREATED)
async def batch_generate(
    request: BatchGenerateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: GenerationEngine = Depends(get_generation_engine),
):
    result = await db.execute(
        select(DirectorPlanModel).where(DirectorPlanModel.id == request.plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    project = await db.get(Project, db_plan.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    from app.services.director import director_service
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


@router.get("/{job_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: GenerationEngine = Depends(get_generation_engine),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.project_id:
        project = await db.get(Project, job.project_id)
        if not project or project.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    status_data = await engine.get_generation_status(job_id)
    if not status_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return GenerationStatusResponse(**status_data)
