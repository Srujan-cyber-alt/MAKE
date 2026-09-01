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
    PlatformPreset,
)
from app.services.creative_director import CreativeDirector, CreativeBrief, ApprovalMode, Genre, Tone
from app.services.storyboard_engine import StoryboardEngine
from app.services.script_engine import ScriptEngine
from app.services.variant_engine import VariantEngine
from app.services.world_system import WorldSystem
from app.services.creative_memory import CreativeMemory
from app.services.brand_dna import BrandDNA
from app.services.generation_learning import GenerationLearning
from app.services.capability_registry import CapabilityRegistry
from app.services.transformation_engine import TransformationEngine
from app.services.before_after import BeforeAfterComparator
from app.services.social_export import SocialExportService
from app.providers.registry import get_provider_registry
from app.services.redis_service import redis_service

router = APIRouter()


def get_provider_registry_safe():
    return get_provider_registry()


def get_transformation_engine() -> TransformationEngine:
    from app.main import transformation_engine
    return transformation_engine


@router.post("/creative-director")
async def create_creative_director(
    objective: str,
    duration_seconds: int = 30,
    aspect_ratio: str = "16:9",
    genre: Optional[str] = None,
    tone: Optional[str] = None,
    audience: Optional[str] = None,
    platform: Optional[str] = None,
    characters: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
    locations: Optional[List[Dict[str, Any]]] = None,
    brand_dna: Optional[Dict[str, Any]] = None,
    reference_assets: Optional[List[str]] = None,
    approval_mode: str = "guided",
    current_user: User = Depends(get_current_user),
):
    try:
        genre_enum = Genre(genre) if genre else Genre.COMMERCIAL
    except ValueError:
        genre_enum = Genre.COMMERCIAL

    try:
        tone_enum = Tone(tone) if tone else Tone.CINEMATIC
    except ValueError:
        tone_enum = Tone.CINEMATIC

    try:
        approval_enum = ApprovalMode(approval_mode)
    except ValueError:
        approval_enum = ApprovalMode.GUIDED

    brief = CreativeBrief(
        objective=objective,
        audience=audience,
        platform=platform,
        genre=genre_enum,
        tone=tone_enum,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        characters=characters or [],
        products=products or [],
        locations=locations or [],
        brand_dna=brand_dna,
        reference_assets=reference_assets or [],
        user_id=current_user.id,
    )
    plan = CreativeDirector.create_creative_director(brief, approval_enum)
    return plan


@router.post("/storyboard")
async def generate_storyboard(
    creative_plan: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    storyboard = StoryboardEngine.generate_storyboard(creative_plan)
    return storyboard


@router.post("/storyboard/regenerate-scene")
async def regenerate_storyboard_scene(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    storyboard = request.get("storyboard", {})
    scene_id = request.get("scene_id", "")
    new_scene_data = request.get("new_scene_data", {})
    updated = StoryboardEngine.regenerate_scene(storyboard, scene_id, new_scene_data)
    return updated


@router.post("/storyboard/regenerate-shot")
async def regenerate_storyboard_shot(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    storyboard = request.get("storyboard", {})
    shot_id = request.get("shot_id", "")
    new_shot_data = request.get("new_shot_data", {})
    updated = StoryboardEngine.regenerate_shot(storyboard, shot_id, new_shot_data)
    return updated


@router.post("/script")
async def generate_script(
    request: Dict[str, Any],
    genre: str = "commercial",
    tone: str = "cinematic",
    duration_seconds: int = 30,
    current_user: User = Depends(get_current_user),
):
    creative_plan = request.get("creative_plan", {})
    try:
        genre_enum = Genre(genre)
    except ValueError:
        genre_enum = Genre.COMMERCIAL

    try:
        tone_enum = Tone(tone)
    except ValueError:
        tone_enum = Tone.CINEMATIC

    script = ScriptEngine.generate_script(
        creative_plan=creative_plan,
        genre=genre_enum,
        tone=tone_enum,
        duration_seconds=duration_seconds,
    )
    return script


@router.post("/variants")
async def generate_variants(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    creative_plan = request.get("creative_plan", {})
    num_variants = request.get("num_variants", 3)
    variation_types = request.get("variation_types")
    variants = VariantEngine.generate_variants(
        creative_plan=creative_plan,
        num_variants=num_variants,
        variation_types=variation_types,
    )
    return variants


@router.post("/worlds")
async def create_world(
    name: str,
    architecture: Optional[str] = None,
    geography: Optional[str] = None,
    lighting: Optional[str] = None,
    weather: Optional[str] = None,
    time: Optional[str] = None,
    colors: Optional[Dict[str, Any]] = None,
    materials: Optional[List[str]] = None,
    props: Optional[List[str]] = None,
    atmosphere: Optional[str] = None,
    spatial_relationships: Optional[Dict[str, Any]] = None,
    reference_images: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
):
    world = await WorldSystem.create_world(
        name=name,
        user_id=current_user.id,
        architecture=architecture,
        geography=geography,
        lighting=lighting,
        weather=weather,
        time=time,
        colors=colors,
        materials=materials,
        props=props,
        atmosphere=atmosphere,
        spatial_relationships=spatial_relationships,
        reference_images=reference_images,
    )
    return world


@router.get("/worlds")
async def list_worlds(current_user: User = Depends(get_current_user)):
    worlds = await WorldSystem.list_worlds(current_user.id)
    return worlds


@router.get("/worlds/{world_id}")
async def get_world(world_id: str, current_user: User = Depends(get_current_user)):
    world = await WorldSystem.get_world(world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")
    return world


@router.post("/worlds/{world_id}/validate")
async def validate_world_consistency(world_id: str, scene: Dict[str, Any], current_user: User = Depends(get_current_user)):
    world = await WorldSystem.get_world(world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")
    result = WorldSystem.validate_world_consistency(world, scene)
    return result


@router.post("/creative-memory")
async def remember_generation(
    project_id: str,
    prompt: str,
    result: Dict[str, Any],
    accepted: bool = True,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    if accepted:
        memory = await CreativeMemory.remember_successful_generation(
            project_id=project_id,
            user_id=current_user.id,
            prompt=prompt,
            result=result,
        )
    else:
        memory = await CreativeMemory.remember_rejected_generation(
            project_id=project_id,
            user_id=current_user.id,
            prompt=prompt,
            result=result,
            reason=reason or "user_rejected",
        )
    return memory


@router.get("/creative-memory/{project_id}")
async def get_project_memory(project_id: str, context_type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    memories = await CreativeMemory.get_project_context(project_id, context_type)
    return memories


@router.post("/brand-dna")
async def create_brand_dna(
    name: str,
    logo: Optional[str] = None,
    colors: Optional[Dict[str, Any]] = None,
    fonts: Optional[List[str]] = None,
    tone: Optional[str] = None,
    visual_style: Optional[str] = None,
    photography_style: Optional[str] = None,
    camera_style: Optional[str] = None,
    music_style: Optional[str] = None,
    language: Optional[str] = None,
    cta_rules: Optional[List[str]] = None,
    product_rules: Optional[List[str]] = None,
    legal_disclaimers: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
):
    brand = await BrandDNA.create_brand_dna(
        user_id=current_user.id,
        name=name,
        logo=logo,
        colors=colors,
        fonts=fonts,
        tone=tone,
        visual_style=visual_style,
        photography_style=photography_style,
        camera_style=camera_style,
        music_style=music_style,
        language=language,
        cta_rules=cta_rules,
        product_rules=product_rules,
        legal_disclaimers=legal_disclaimers,
    )
    return brand


@router.get("/brand-dna")
async def list_brands(current_user: User = Depends(get_current_user)):
    brands = await BrandDNA.list_brands(current_user.id)
    return brands


@router.post("/brand-dna/{brand_id}/validate")
async def validate_brand_compliance(brand_id: str, content: Dict[str, Any], current_user: User = Depends(get_current_user)):
    result = await BrandDNA.validate_against_brand(brand_id, content)
    return result


@router.get("/learning/model-performance")
async def get_model_performance(model_id: str, provider_id: str, current_user: User = Depends(get_current_user)):
    stats = await GenerationLearning.get_model_performance(model=model_id, provider=provider_id)
    return stats


@router.get("/learning/best-models")
async def get_best_models(capability: str, limit: int = 5, current_user: User = Depends(get_current_user)):
    models = await GenerationLearning.get_best_models_for_capability(capability=capability, limit=limit)
    return models


@router.post("/learning/record")
async def record_generation_event(
    prompt: str,
    model: str,
    provider: str,
    settings: Dict[str, Any],
    output_quality: float,
    repair_count: int = 0,
    failure_type: Optional[str] = None,
    user_iteration: int = 1,
    user_accepted: bool = False,
    generation_time_seconds: float = 0.0,
    cost: float = 0.0,
    current_user: User = Depends(get_current_user),
):
    event = await GenerationLearning.record_generation_event(
        prompt=prompt,
        model=model,
        provider=provider,
        settings=settings,
        output_quality=output_quality,
        repair_count=repair_count,
        failure_type=failure_type,
        user_iteration=user_iteration,
        user_accepted=user_accepted,
        generation_time_seconds=generation_time_seconds,
        cost=cost,
    )
    return event
