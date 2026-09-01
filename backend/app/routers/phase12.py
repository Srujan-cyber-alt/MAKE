from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User
from app.schemas.phase9 import (
    UserMode,
    ShotRepairRequest,
)
from app.services.universal_command_engine import UniversalCommandEngine, ParsedCommand, CommandIntent
from app.services.media_understanding import MediaUnderstanding
from app.services.video_extension_engine import VideoExtensionEngine
from app.services.image_to_video_engine import ImageToVideoEngine
from app.services.video_to_video_engine import VideoToVideoEngine
from app.services.character_performance_engine import CharacterPerformanceEngine
from app.services.real_time_progress import RealTimeProgress
from app.services.asset_intelligence import AssetIntelligence
from app.services.make_auto_mode import MakeAutoMode
from app.services.capability_registry import CapabilityRegistry
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode, Genre, Tone
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
from app.services.variant_engine import VariantEngine
from app.services.world_system import WorldSystem
from app.services.creative_memory import CreativeMemory
from app.services.brand_dna import BrandDNA
from app.services.generation_learning import GenerationLearning
from app.services.transformation_engine import TransformationEngine
from app.providers.registry import get_provider_registry
from app.services.redis_service import redis_service

router = APIRouter()


def get_provider_registry_safe():
    return get_provider_registry()


def get_transformation_engine() -> TransformationEngine:
    from app.main import transformation_engine
    return transformation_engine


@router.post("/command")
async def interpret_command(command: str, context: Optional[Dict[str, Any]] = None, current_user: User = Depends(get_current_user)):
    parsed = UniversalCommandEngine.parse(command, context)
    plan = UniversalCommandEngine.to_execution_plan(parsed)
    return plan


@router.post("/understand-asset")
async def understand_asset(asset_id: str, asset_type: str = "video", current_user: User = Depends(get_current_user)):
    result = await MediaUnderstanding.understand_asset(asset_id, asset_type, current_user.id)
    return result


@router.post("/extend-video")
async def extend_video(
    source_asset_id: str,
    project_id: str,
    extend_position: str = "end",
    extend_duration_seconds: float = 5.0,
    preserve_identity: bool = True,
    preserve_camera: bool = True,
    preserve_lighting: bool = True,
    preserve_motion: bool = True,
    world_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    engine: TransformationEngine = Depends(get_transformation_engine),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await VideoExtensionEngine.extend_video(
        source_asset_id=source_asset_id,
        project_id=project_id,
        user_id=current_user.id,
        extend_position=extend_position,
        extend_duration_seconds=extend_duration_seconds,
        preserve_identity=preserve_identity,
        preserve_camera=preserve_camera,
        preserve_lighting=preserve_lighting,
        preserve_motion=preserve_motion,
        world_id=world_id,
    )
    return result


@router.post("/image-to-video")
async def image_to_video(
    source_asset_id: str,
    project_id: str,
    prompt: str,
    duration_seconds: float = 5.0,
    character_references: Optional[List[str]] = None,
    product_references: Optional[List[str]] = None,
    world_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    engine: TransformationEngine = Depends(get_transformation_engine),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await ImageToVideoEngine.create_video_from_image(
        source_asset_id=source_asset_id,
        project_id=project_id,
        user_id=current_user.id,
        prompt=prompt,
        duration_seconds=duration_seconds,
        character_references=character_references,
        product_references=product_references,
        world_id=world_id,
        brand_id=brand_id,
    )
    return result


@router.post("/video-to-video")
async def video_to_video(
    source_asset_id: str,
    project_id: str,
    prompt: str,
    preserve_person: bool = False,
    preserve_product: bool = False,
    preserve_camera: bool = False,
    preserve_motion: bool = False,
    preserve_background: bool = False,
    character_references: Optional[List[str]] = None,
    product_references: Optional[List[str]] = None,
    world_id: Optional[str] = None,
    style_strength: float = 0.8,
    current_user: User = Depends(get_current_user),
    engine: TransformationEngine = Depends(get_transformation_engine),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await VideoToVideoEngine.transform_video(
        source_asset_id=source_asset_id,
        project_id=project_id,
        user_id=current_user.id,
        prompt=prompt,
        preserve_person=preserve_person,
        preserve_product=preserve_product,
        preserve_camera=preserve_camera,
        preserve_motion=preserve_motion,
        preserve_background=preserve_background,
        character_references=character_references,
        product_references=product_references,
        world_id=world_id,
        style_strength=style_strength,
    )
    return result


@router.post("/character-performance")
async def plan_character_performance(
    character_id: str,
    prompt: str,
    duration_seconds: float = 5.0,
    shot_id: Optional[str] = None,
    motion_reference_ids: Optional[List[str]] = None,
    pose_reference_ids: Optional[List[str]] = None,
    facial_reference_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
):
    result = await CharacterPerformanceEngine.plan_performance(
        character_id=character_id,
        prompt=prompt,
        duration_seconds=duration_seconds,
        shot_id=shot_id,
        motion_reference_ids=motion_reference_ids,
        pose_reference_ids=pose_reference_ids,
        facial_reference_ids=facial_reference_ids,
    )
    return result


@router.get("/progress/{pipeline_id}")
async def get_progress(pipeline_id: str, current_user: User = Depends(get_current_user)):
    progress = await RealTimeProgress.get_progress(pipeline_id)
    return progress


@router.post("/asset-intelligence")
async def classify_asset(asset_id: str, asset_type: str = "video", current_user: User = Depends(get_current_user)):
    result = await AssetIntelligence.classify_asset(asset_id, asset_type, current_user.id)
    return result


@router.get("/asset-intelligence/search")
async def search_assets(query: str, project_id: str, current_user: User = Depends(get_current_user)):
    results = await AssetIntelligence.semantic_search(project_id, query, current_user.id)
    return results


@router.post("/make-auto")
async def make_auto(
    project_id: str,
    prompt: str,
    source_asset_ids: Optional[List[str]] = None,
    brand_id: Optional[str] = None,
    world_id: Optional[str] = None,
    character_ids: Optional[List[str]] = None,
    product_ids: Optional[List[str]] = None,
    approval_mode: str = "auto",
    current_user: User = Depends(get_current_user),
    engine: TransformationEngine = Depends(get_transformation_engine),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await MakeAutoMode.execute(
        user_id=current_user.id,
        project_id=project_id,
        prompt=prompt,
        source_asset_ids=source_asset_ids,
        brand_id=brand_id,
        world_id=world_id,
        character_ids=character_ids,
        product_ids=product_ids,
        approval_mode=approval_mode,
    )
    return result


@router.get("/capabilities")
async def get_capabilities(current_user: User = Depends(get_current_user)):
    capabilities = await CapabilityRegistry.get_all_capabilities()
    return capabilities
