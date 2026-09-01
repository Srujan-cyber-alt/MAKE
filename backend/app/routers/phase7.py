from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User, Asset
from app.schemas.transformation import TransformationRequest
from app.schemas.phase7 import (
    VisualAnalyzerResponse,
    SegmentationResult,
    TrackingResult,
    FrameExtractionResult,
    SmartTargetSelection,
    QualityGateResult,
    VersionSnapshot,
    PromptIterationHistory,
    BackgroundReplacementParams,
    MotionTransferParams,
)
from app.services.visual_analyzer import VisualAnalyzer
from app.services.segmentation_service import SegmentationService
from app.services.tracking_service import TrackingService
from app.services.frame_processor import frame_processor
from app.services.smart_target_selector import SmartTargetSelector
from app.services.quality_gates import QualityGates
from app.services.versioning import VersionWorkflow
from app.services.background_replacement_service import BackgroundReplacementService
from app.services.motion_transfer_service import MotionTransferService
from app.services.transformation_engine import TransformationEngine

router = APIRouter()


def get_transformation_engine() -> TransformationEngine:
    from app.main import transformation_engine
    return transformation_engine


@router.get("/visual-analysis/{asset_id}", response_model=VisualAnalyzerResponse)
async def get_visual_analysis(
    asset_id: str,
    project_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await VisualAnalyzer.analyze_video(
        asset_id=asset_id,
        project_id=project_id,
        user_id=current_user.id,
    )
    return result


@router.get("/smart-target/{asset_id}", response_model=SmartTargetSelection)
async def get_smart_target(
    asset_id: str,
    project_id: str,
    prompt: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    visual_response = await VisualAnalyzer.analyze_video(
        asset_id=asset_id,
        project_id=project_id,
        user_id=current_user.id,
    )
    detected_targets = visual_response.get("objects", []) + visual_response.get("faces", [])
    result = await SmartTargetSelector.select_target(
        prompt=prompt,
        detected_targets=detected_targets,
        asset_id=asset_id,
        project_id=project_id,
        user_id=current_user.id,
    )
    return result


@router.post("/quality-gate/{asset_id}", response_model=QualityGateResult)
async def run_quality_gate(
    asset_id: str,
    identity_required: bool = False,
    product_required: bool = False,
    current_user: User = Depends(get_current_user),
):
    asset_path = f"/tmp/{asset_id}.mp4"
    result = await QualityGates.evaluate(
        video_path=asset_path,
        identity_required=identity_required,
        product_required=product_required,
    )
    return result


@router.get("/versions/{project_id}", response_model=List[Dict[str, Any]])
async def list_versions(
    project_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await VersionWorkflow.get_version_history(project_id)


@router.post("/versions/{project_id}", response_model=VersionSnapshot)
async def create_version(
    project_id: str,
    request: TransformationRequest,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    snapshot = await VersionWorkflow.create_version(
        project_id=project_id,
        prompt=request.prompt,
        operations=[op.model_dump() for op in request.operations],
        asset_ids=[request.source_asset_id],
        user_id=current_user.id,
    )
    return snapshot


@router.get("/segmentation/{asset_id}", response_model=SegmentationResult)
async def segment_asset(
    asset_id: str,
    project_id: str,
    mask_type: str = "person",
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if mask_type == "person":
        result = await SegmentationService.segment_person(asset_id=asset_id)
    elif mask_type == "background":
        result = await SegmentationService.segment_background(asset_id=asset_id)
    else:
        result = await SegmentationService.segment_object(asset_id=asset_id, object_label=mask_type)
    return result


@router.get("/tracking/{asset_id}", response_model=TrackingResult)
async def track_asset(
    asset_id: str,
    project_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await TrackingService.track_person(asset_id=asset_id)
    return result


@router.post("/background-replacement/{asset_id}", response_model=Dict[str, Any])
async def replace_background_endpoint(
    asset_id: str,
    project_id: str,
    background_prompt: Optional[str] = None,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    params = BackgroundReplacementParams(background_prompt=background_prompt)
    result = await BackgroundReplacementService.replace_background(
        asset_id=asset_id,
        project_id=project_id,
        user_id=current_user.id,
        params=params,
    )
    return result


@router.post("/motion-transfer/{asset_id}", response_model=Dict[str, Any])
async def motion_transfer_endpoint(
    asset_id: str,
    project_id: str,
    motion_strength: float = 0.8,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    params = MotionTransferParams(motion_strength=motion_strength)
    result = await MotionTransferService.transfer_motion(
        asset_id=asset_id,
        project_id=project_id,
        user_id=current_user.id,
        params=params,
    )
    return result
