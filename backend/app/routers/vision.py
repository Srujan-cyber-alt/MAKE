from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, VisionAnalysis
from app.services.vision_pipeline import VisionPipeline
from app.services.vision_runtime import VisionRuntime
from app.services.vision_model_registry import ModelRegistry
import uuid

router = APIRouter()


@router.get("/runtime")
async def get_vision_runtime(current_user: User = Depends(get_current_user)):
    return VisionPipeline.get_capabilities()


@router.get("/models")
async def get_vision_models(current_user: User = Depends(get_current_user)):
    return VisionPipeline.get_model_registry()


@router.post("/assets/{asset_id}/analyze")
async def analyze_asset(asset_id: str, request: Dict[str, Any], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sample_rate = request.get("sample_rate", 1)
    analysis_type = request.get("analysis_type", "full")
    frames = request.get("frames")
    frame_indices = request.get("frame_indices")
    timestamps = request.get("timestamps")
    analysis = VisionAnalysis(
        id=str(uuid.uuid4()),
        project_id=request.get("project_id", ""),
        asset_id=asset_id,
        user_id=current_user.id,
        status="processing",
        analysis_type=analysis_type,
        backend="unified",
        progress=0.0,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    result = await VisionPipeline.analyze_asset(
        asset_id=asset_id,
        frames=frames,
        frame_indices=frame_indices,
        timestamps=timestamps,
        sample_rate=sample_rate,
    )
    analysis.status = result.status
    analysis.progress = result.progress
    analysis.result_summary = result.to_dict()
    analysis.error = result.error
    analysis.completed_at = __import__('datetime').datetime.utcnow().timestamp()
    await db.commit()
    await db.refresh(analysis)
    return {"analysis_id": analysis.id, "status": analysis.status, "result": result.to_dict()}


@router.get("/assets/{asset_id}/analysis")
async def get_asset_analysis(asset_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(
        select(VisionAnalysis).where(VisionAnalysis.asset_id == asset_id).order_by(VisionAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        cached = await VisionPipeline.get_cached_result(asset_id)
        if cached:
            return cached
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis found")
    return {"analysis_id": analysis.id, "status": analysis.status, "result_summary": analysis.result_summary, "error": analysis.error}


@router.get("/jobs/{analysis_id}")
async def get_vision_job(analysis_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(VisionAnalysis).where(VisionAnalysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"analysis_id": analysis.id, "status": analysis.status, "progress": analysis.progress, "stage": analysis.analysis_type, "error": analysis.error}
