from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User
from app.schemas.phase9 import (
    GenerativeModelInfo,
    UserMode,
    CinematicPromptCompilation,
    TemporalConsistencyReport,
    IdentityProfile,
    CharacterDefinition,
    ProductDefinition,
    CameraDefinition,
    MotionDefinition,
    KeyframeDefinition,
    V2VWorkflowRequest,
    ShotRepairRequest,
    UnifiedQualityScore,
    GenerationIteration,
    ColorLookAdjustment,
    CaptionTrack,
    AudioTrack,
    GenerationJobGraph,
    CostTracking,
    PlatformPreset,
)
from app.services.generative_model_abstraction import GenerativeModelAbstraction
from app.services.smart_model_router import SmartModelRouter
from app.services.advanced_prompt_compiler import AdvancedPromptCompiler
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.identity_lock_v2 import IdentityLockV2
from app.services.character_system import CharacterSystem
from app.services.product_system import ProductSystem
from app.services.camera_control_engine import CameraControlEngine
from app.services.motion_engine import MotionEngine
from app.services.keyframe_system_v2 import KeyframeSystemV2
from app.services.v2v_engine import V2VEngine
from app.services.shot_repair_engine import ShotRepairEngine
from app.services.unified_quality_scoring import UnifiedQualityScoring
from app.services.generation_iteration import GenerationIterationSystem
from app.services.audio_system import AudioSystem
from app.services.caption_system import CaptionSystem
from app.services.color_look_engine import ColorLookEngine
from app.services.before_after import BeforeAfterComparator
from app.services.social_export import SocialExportService
from app.providers.registry import get_provider_registry
from app.services.transformation_engine import TransformationEngine

router = APIRouter()


def get_provider_registry_safe():
    return get_provider_registry()


def get_transformation_engine() -> TransformationEngine:
    from app.main import transformation_engine
    return transformation_engine


@router.get("/models", response_model=List[GenerativeModelInfo])
async def list_models(current_user: User = Depends(get_current_user)):
    registry = get_provider_registry_safe()
    return await GenerativeModelAbstraction.get_all_models(registry)


@router.post("/route", response_model=Dict[str, Any])
async def route_model(
    required_capabilities: List[str],
    duration_seconds: float = 10.0,
    aspect_ratio: str = "16:9",
    reference_count: int = 0,
    user_mode: str = UserMode.AUTO,
    current_user: User = Depends(get_current_user),
):
    registry = get_provider_registry_safe()
    router_instance = SmartModelRouter(provider_registry=registry)
    caps = [c for c in required_capabilities if c in [e.value for e in __import__('app.schemas.phase9', fromlist=['ModelCapabilityDetail']).ModelCapabilityDetail]]
    return await router_instance.route(
        required_capabilities=caps,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        reference_count=reference_count,
        user_mode=user_mode,
    )


@router.post("/compile-prompt", response_model=CinematicPromptCompilation)
async def compile_prompt(prompt: str, context: Optional[Dict[str, Any]] = None):
    return AdvancedPromptCompiler.compile_from_prompt(prompt, context)


@router.get("/temporal/{asset_id}", response_model=TemporalConsistencyReport)
async def analyze_temporal(
    asset_id: str,
    project_id: str,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    source_path = await BeforeAfterComparator._resolve_asset_path(asset_id, project_id, current_user.id)
    if not source_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return await TemporalConsistencyEngine.analyze(source_path)


@router.post("/identity", response_model=IdentityProfile)
async def create_identity_profile(
    entity_type: str,
    name: str,
    reference_asset_ids: List[str] = [],
    mode: str = "balanced",
    attributes: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
):
    return await IdentityLockV2.create_profile(entity_type, name, reference_asset_ids, mode, attributes)


@router.get("/identity/{profile_id}", response_model=Dict[str, Any])
async def get_identity_profile(profile_id: str, current_user: User = Depends(get_current_user)):
    profile = await IdentityLockV2.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.post("/characters", response_model=CharacterDefinition)
async def create_character(
    name: str,
    age_range: Optional[str] = None,
    appearance: Optional[Dict[str, Any]] = None,
    hair: Optional[Dict[str, Any]] = None,
    face: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    clothing: Optional[Dict[str, Any]] = None,
    accessories: Optional[List[str]] = None,
    personality: Optional[str] = None,
    voice: Optional[str] = None,
    movement: Optional[Dict[str, Any]] = None,
    reference_images: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
):
    return await CharacterSystem.create_character(
        name=name,
        age_range=age_range,
        appearance=appearance,
        hair=hair,
        face=face,
        body=body,
        clothing=clothing,
        accessories=accessories,
        personality=personality,
        voice=voice,
        movement=movement,
        reference_images=reference_images,
    )


@router.get("/characters/{character_id}", response_model=Dict[str, Any])
async def get_character(character_id: str, current_user: User = Depends(get_current_user)):
    character = await CharacterSystem.get_character(character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return character


@router.post("/products", response_model=ProductDefinition)
async def create_product(
    name: str,
    shape: Optional[Dict[str, Any]] = None,
    dimensions: Optional[Dict[str, Any]] = None,
    materials: Optional[List[str]] = None,
    colors: Optional[Dict[str, Any]] = None,
    logos: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    packaging: Optional[Dict[str, Any]] = None,
    brand_marks: Optional[List[str]] = None,
    orientation: Optional[str] = None,
    surface_details: Optional[List[str]] = None,
    reference_images: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
):
    return await ProductSystem.create_product(
        name=name,
        shape=shape,
        dimensions=dimensions,
        materials=materials,
        colors=colors,
        logos=logos,
        labels=labels,
        packaging=packaging,
        brand_marks=brand_marks,
        orientation=orientation,
        surface_details=surface_details,
        reference_images=reference_images,
    )


@router.post("/camera", response_model=CameraDefinition)
async def parse_camera(prompt: str, current_user: User = Depends(get_current_user)):
    return CameraControlEngine.parse_natural_language(prompt)


@router.post("/motion", response_model=List[MotionDefinition])
async def parse_motion(prompt: str, current_user: User = Depends(get_current_user)):
    return MotionEngine.parse_natural_language(prompt)


@router.post("/keyframes", response_model=List[KeyframeDefinition])
async def create_keyframes(
    prompt: str,
    frame_range_start: int = 0,
    frame_range_end: int = 30,
    current_user: User = Depends(get_current_user),
):
    return KeyframeSystemV2.parse_natural_language(prompt, frame_range_start, frame_range_end)


@router.post("/v2v", response_model=Dict[str, Any])
async def execute_v2v(
    request: V2VWorkflowRequest,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(request.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await V2VEngine.execute(request, current_user.id)


@router.post("/repair", response_model=Dict[str, Any])
async def repair_shot(
    request: ShotRepairRequest,
    video_path: str,
    current_user: User = Depends(get_current_user),
):
    return await ShotRepairEngine.repair(request, video_path)


@router.get("/quality/{asset_id}", response_model=UnifiedQualityScore)
async def unified_quality(
    asset_id: str,
    project_id: str,
    identity_required: bool = False,
    product_required: bool = False,
    engine: TransformationEngine = Depends(get_transformation_engine),
    current_user: User = Depends(get_current_user),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    source_path = await BeforeAfterComparator._resolve_asset_path(asset_id, project_id, current_user.id)
    if not source_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return await UnifiedQualityScoring.score(
        video_path=source_path,
        identity_required=identity_required,
        product_required=product_required,
    )


@router.post("/iterations", response_model=GenerationIteration)
async def create_iteration(
    project_id: str,
    prompt: str,
    shot_id: Optional[str] = None,
    parent_iteration_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    references: Optional[List[str]] = None,
    seed: Optional[int] = None,
    parameters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
):
    return await GenerationIterationSystem.create_iteration(
        project_id=project_id,
        prompt=prompt,
        shot_id=shot_id,
        parent_iteration_id=parent_iteration_id,
        provider=provider,
        model=model,
        references=references,
        seed=seed,
        parameters=parameters,
    )


@router.get("/iterations/{project_id}", response_model=List[Dict[str, Any]])
async def list_iterations(project_id: str, shot_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    return await GenerationIterationSystem.list_iterations(project_id, shot_id)


@router.post("/audio/track", response_model=AudioTrack)
async def create_audio_track(
    track_id: str,
    track_type: str,
    source: Optional[str] = None,
    volume: float = 1.0,
    current_user: User = Depends(get_current_user),
):
    return await AudioSystem.create_track(track_id, track_type, source, volume)


@router.post("/captions", response_model=CaptionTrack)
async def create_captions(
    prompt: str,
    duration_seconds: float = 30.0,
    burn_in: bool = False,
    current_user: User = Depends(get_current_user),
):
    return await CaptionSystem.generate_captions_from_prompt(prompt, duration_seconds)


@router.get("/captions/{track_id}/srt")
async def export_caption_srt(track_id: str, current_user: User = Depends(get_current_user)):
    track_data = await CaptionSystem.create_track(track_id=track_id)
    srt = await CaptionSystem.export_srt(track_data)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=srt, media_type="text/plain")


@router.post("/color-look", response_model=Dict[str, Any])
async def apply_color_look(
    source_path: str,
    output_path: str,
    current_user: User = Depends(get_current_user),
):
    adjustment = ColorLookAdjustment(preset="cinematic")
    return ColorLookEngine.apply_look(source_path, output_path, adjustment)


@router.get("/social-presets", response_model=List[Dict[str, Any]])
async def list_social_presets(current_user: User = Depends(get_current_user)):
    return SocialExportService.list_presets()


@router.get("/capabilities")
async def get_capabilities(current_user: User = Depends(get_current_user)):
    from app.services.capability_registry import CapabilityRegistry
    return await CapabilityRegistry.get_all_capabilities()


@router.post("/export")
async def export_video(
    source_path: str,
    output_path: str,
    platform: str = "youtube",
    custom_resolution: Optional[str] = None,
    custom_fps: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    from app.services.export_engine import ExportEngine
    return await ExportEngine.export_video(
        source_path=source_path,
        output_path=output_path,
        platform=platform,
        custom_resolution=custom_resolution,
        custom_fps=custom_fps,
    )


@router.post("/pipeline/execute")
async def execute_unified_pipeline(
    project_id: str,
    prompt: str,
    source_asset_id: Optional[str] = None,
    operations: Optional[List[Dict[str, Any]]] = None,
    preserve_identity: bool = True,
    current_user: User = Depends(get_current_user),
    engine: TransformationEngine = Depends(get_transformation_engine),
):
    project = await engine._get_project_for_user(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    from app.services.unified_video_pipeline import UnifiedVideoPipeline
    from app.services.transformation_executor_v2 import TransformationExecutorV2
    from app.schemas.transformation import TransformationRequest, TransformationOperation
    from app.services.target_selection_workflow import TargetSelectionWorkflow

    operations_list = []
    for op in (operations or []):
        operations_list.append(TransformationOperation(**op))

    request = TransformationRequest(
        project_id=project_id,
        source_asset_id=source_asset_id or "",
        prompt=prompt,
        operations=operations_list,
        preserve_identity=preserve_identity,
    )

    state = UnifiedVideoPipeline.create_pipeline(project_id=project_id, user_id=current_user.id)

    async def executor(pipeline_state):
        if source_asset_id and prompt:
            selection = await TargetSelectionWorkflow.select_target(
                prompt=prompt,
                asset_id=source_asset_id,
                project_id=project_id,
                user_id=current_user.id,
            )
            if selection.get("selected_target") and not request.operations:
                request.operations = [
                    TransformationOperation(
                        type="style_transfer",
                        target={"type": selection["selected_target"].get("category", "object"), "description": selection["selected_target"].get("label", "")},
                    )
                ]
        return await TransformationExecutorV2.execute_transformation(request, current_user.id, pipeline_state)

    from app.services.unified_video_pipeline import PipelineStage
    result_node = await UnifiedVideoPipeline.execute_stage(state, PipelineStage.GENERATION, executor)
    return {
        "pipeline_id": state.pipeline_id,
        "status": result_node.status,
        "output": result_node.output,
        "error": result_node.error,
        "progress": state.progress,
    }
