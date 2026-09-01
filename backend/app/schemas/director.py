from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IntentExtraction(BaseModel):
    objective: str
    content_type: str
    subject: Optional[str] = None
    audience: Optional[str] = None
    tone: str = "professional"
    style: Optional[str] = None
    story: Optional[str] = None
    total_duration_seconds: int = 30
    aspect_ratio: str = "16:9"
    resolution: str = "1080p"
    platform: Optional[str] = None
    references: List[str] = []
    characters: List[str] = []
    products: List[str] = []
    locations: List[str] = []
    audio: Dict[str, Any] = {}
    voiceover: bool = False
    music: bool = False
    captions: bool = False
    cta: Optional[str] = None


class CameraRequirement(BaseModel):
    movement: str = "static"
    lens: str = "50mm"
    aperture: Optional[str] = None
    depth_of_field: Optional[str] = None
    focus: Optional[str] = None
    motion_blur: Optional[str] = None
    camera_height: Optional[str] = None
    camera_angle: Optional[str] = None


class AssetRequirement(BaseModel):
    id: str
    type: str
    role: str
    description: str
    required: bool = True
    reference_asset_id: Optional[str] = None
    requirements: List[str] = []


class ContinuityRequirement(BaseModel):
    id: str
    type: str
    description: str
    applies_to: List[str]
    rules: List[str] = []


class GenerationRequirement(BaseModel):
    id: str
    method: str
    provider: Optional[str] = None
    model: Optional[str] = None
    required_capabilities: List[str] = []
    parameters: Dict[str, Any] = {}


class AudioRequirement(BaseModel):
    id: str
    type: str
    description: str
    duration_seconds: float
    parameters: Dict[str, Any] = {}


class ExportRequirement(BaseModel):
    id: str
    aspect_ratio: str
    resolution: str
    fps: int = 24
    format: str = "mp4"
    platform: Optional[str] = None
    duration_seconds: float


class ShotPlan(BaseModel):
    id: str
    scene_id: str
    order: int
    description: str
    subject: Optional[str] = None
    action: Optional[str] = None
    environment: Optional[str] = None
    camera: CameraRequirement
    lighting: Optional[str] = None
    composition: Optional[str] = None
    style: Optional[str] = None
    motion: Optional[str] = None
    duration_seconds: float
    references: List[str] = []
    characters: List[str] = []
    products: List[str] = []
    locations: List[str] = []
    audio: List[str] = []
    continuity: List[str] = []
    generation: Optional[GenerationRequirement] = None
    status: str = "planned"


class ScenePlan(BaseModel):
    id: str
    order: int
    title: str
    purpose: str
    description: str
    environment: Optional[str] = None
    duration_seconds: float
    shots: List[ShotPlan]
    references: List[str] = []
    characters: List[str] = []
    products: List[str] = []
    locations: List[str] = []
    continuity: List[str] = []


class DirectorPlan(BaseModel):
    id: str
    project_id: str
    title: str
    creative_concept: str
    objective: str
    content_type: str
    audience: Optional[str] = None
    tone: str
    style: Optional[str] = None
    duration: int
    aspect_ratio: str
    resolution: str
    platform: Optional[str] = None
    scenes: List[ScenePlan]
    asset_requirements: List[AssetRequirement]
    continuity_requirements: List[ContinuityRequirement]
    audio_requirements: List[AudioRequirement]
    export_requirements: ExportRequirement
    generation_requirements: List[GenerationRequirement]
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class DirectorRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    project_id: Optional[str] = None
    reference_asset_ids: List[str] = []
    character_ids: List[str] = []
    product_ids: List[str] = []
    location_ids: List[str] = []
    preferences: Dict[str, Any] = {}


class DirectorPlanResponse(BaseModel):
    id: str
    project_id: str
    title: str
    creative_concept: str
    objective: str
    content_type: str
    audience: Optional[str] = None
    tone: str
    style: Optional[str] = None
    duration: int
    aspect_ratio: str
    resolution: str
    platform: Optional[str] = None
    scenes: List[Dict[str, Any]]
    asset_requirements: List[Dict[str, Any]]
    continuity_requirements: List[Dict[str, Any]]
    audio_requirements: List[Dict[str, Any]]
    export_requirements: Dict[str, Any]
    generation_requirements: List[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        extra = 'ignore'


class DirectorPlanCreate(BaseModel):
    prompt: str = Field(..., min_length=1)
    project_id: Optional[str] = None
    reference_asset_ids: List[str] = []
    character_ids: List[str] = []
    product_ids: List[str] = []
    location_ids: List[str] = []
    preferences: Dict[str, Any] = {}


class DirectorPlanUpdate(BaseModel):
    title: Optional[str] = None
    creative_concept: Optional[str] = None
    duration: Optional[int] = None
    aspect_ratio: Optional[str] = None
    style: Optional[str] = None
    status: Optional[str] = None
    preferences: Dict[str, Any] = {}
