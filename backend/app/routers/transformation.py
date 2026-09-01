from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User
from app.schemas.transformation import (
    TransformationRequest,
    TransformationResponse,
    TransformationStatusResponse,
    BatchTransformationRequest,
    TransformationAnalyzeResponse,
    MaskRequest,
    MaskResponse,
)
from app.services.transformation_engine import TransformationEngine
from app.services.transformation_analyzer import TransformationAnalyzer

router = APIRouter()


def get_transformation_engine() -> TransformationEngine:
    from app.main import transformation_engine
    return transformation_engine


@router.post("/analyze", response_model=TransformationAnalyzeResponse)
async def analyze_transformation(
    request: TransformationRequest,
    current_user: User = Depends(get_current_user),
):
    project = await get_transformation_engine()._get_project_for_user(request.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    source_asset_context = {
        "reference_asset_ids": request.references,
        "project_id": request.project_id,
    }
    analysis = TransformationAnalyzer.analyze(request.prompt, source_asset_context)
    return TransformationAnalyzeResponse(**analysis)


@router.post("/plan", response_model=dict)
async def create_transformation_plan(
    request: TransformationRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.transformation_planner import TransformationPlanner

    project = await get_transformation_engine()._get_project_for_user(request.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    plan = TransformationPlanner.create_plan(
        project_id=request.project_id,
        source_asset_id=request.source_asset_id,
        operations=request.operations,
        preferences=request.preferences,
    )
    return plan


@router.post("/execute", response_model=TransformationResponse, status_code=status.HTTP_201_CREATED)
async def execute_transformation(
    request: TransformationRequest,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await engine._get_project_for_user(request.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await engine.execute_transformation(request, current_user.id)
    return TransformationResponse(
        id=result["transformation_id"],
        project_id=result["project_id"],
        source_asset_id=result["source_asset_id"],
        status=result["status"],
        plan=result.get("plan", {}),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.get("/{transformation_id}/status", response_model=TransformationStatusResponse)
async def get_transformation_status(
    transformation_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    status = await engine.get_status(transformation_id)
    if not status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transformation not found")
    return status


@router.post("/{transformation_id}/cancel")
async def cancel_transformation(
    transformation_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    success = await engine.cancel_transformation(transformation_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transformation not found or already completed")
    return {"status": "cancelled", "transformation_id": transformation_id}


@router.post("/mask", response_model=MaskResponse)
async def create_mask(
    request: MaskRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.mask_engine import MaskEngine
    mask = MaskEngine.create_mask(request)
    return mask


@router.get("/projects/{project_id}", response_model=List[dict])
async def list_project_transformations(
    project_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    transformations = []
    for tid, record in engine.active_transformations.items():
        if record.get("project_id") == project_id:
            transformations.append(record)
    return transformations


@router.post("/batch", response_model=dict)
async def batch_transformation(
    request: BatchTransformationRequest,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(request.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    results = []
    for source_asset_id in request.source_asset_ids:
        req = TransformationRequest(
            project_id=request.project_id,
            source_asset_id=source_asset_id,
            prompt=request.prompt,
            operations=request.operations,
            references=request.references,
            preferences=request.preferences,
            preserve_identity=request.preserve_identity,
            preserve_background=request.preserve_background,
            strength=request.strength,
        )
        result = await engine.execute_transformation(req, current_user.id)
        results.append(result)

    return {"batch_id": str(uuid.uuid4()), "results": results, "total": len(results)}