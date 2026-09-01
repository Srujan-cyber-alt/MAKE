from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TransformationType(str, Enum):
    OBJECT_REMOVAL = "object_removal"
    OBJECT_REPLACEMENT = "object_replacement"
    BACKGROUND_REPLACEMENT = "background_replacement"
    STYLE_TRANSFER = "style_transfer"
    MOTION_TRANSFER = "motion_transfer"
    CAMERA_TRANSFORM = "camera_transform"
    VFX_APPLY = "vfx_apply"
    INPAINTING = "inpainting"
    OUTPAINTING = "outpainting"
    ENVIRONMENT_TRANSFORM = "environment_transform"
    IDENTITY_PRESERVE = "identity_preserve"
    ACTION_TRANSFORM = "action_transform"
    LIGHTING_TRANSFORM = "lighting_transform"
    WEATHER_TRANSFORM = "weather_transform"
    VIDEO_TO_VIDEO = "video_to_video"


class TargetSelectorType(str, Enum):
    PERSON = "person"
    OBJECT = "object"
    BACKGROUND = "background"
    FACE = "face"
    PRODUCT = "product"
    TEXT = "text"
    LIGHTING = "lighting"
    CAMERA = "camera"
    ENVIRONMENT = "environment"
    CUSTOM = "custom"


class TargetSelector(BaseModel):
    type: TargetSelectorType
    description: str
    reference_asset_ids: List[str] = []
    confidence: float = 1.0
    bounding_box: Optional[Dict[str, Any]] = None
    track_id: Optional[str] = None


class BlendMode(str, Enum):
    OVERLAY = "overlay"
    SCREEN = "screen"
    MULTIPLY = "multiply"
    ADD = "add"
    NORMAL = "normal"
    SOFT_LIGHT = "soft_light"


class VFXLayerType(str, Enum):
    FIRE = "fire"
    SMOKE = "smoke"
    DUST = "dust"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    SPARKS = "sparks"
    LIGHTNING = "lightning"
    GLOW = "glow"
    EXPLOSION = "explosion"
    ENERGY = "energy"
    ATMOSPHERIC = "atmospheric"
    DEBRIS = "debris"
    CINEMATIC_PARTICLES = "cinematic_particles"


class VFXLayer(BaseModel):
    layer_type: VFXLayerType
    blend_mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0
    position: Optional[Dict[str, Any]] = None
    intensity: float = 1.0
    duration_seconds: Optional[float] = None
    frame_range: Optional[Dict[str, int]] = None
    parameters: Dict[str, Any] = {}


class TransformationOperation(BaseModel):
    type: TransformationType
    target: Optional[TargetSelector] = None
    parameters: Dict[str, Any] = {}
    references: List[str] = []
    preserve_identity: bool = False
    preserve_background: bool = False
    strength: float = 0.8
    seed: Optional[int] = None
    frame_range: Optional[Dict[str, int]] = None
    dependencies: List[str] = []
    vfx_layers: List[VFXLayer] = []


class TransformationPlan(BaseModel):
    id: str
    project_id: str
    source_asset_id: str
    operations: List[TransformationOperation]
    references: List[str] = []
    temporal_constraints: Dict[str, Any] = {}
    identity_constraints: Dict[str, Any] = {}
    output_requirements: Dict[str, Any] = {}
    status: str = "draft"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        extra = 'ignore'


class TransformationRequest(BaseModel):
    project_id: str
    source_asset_id: str
    prompt: str = Field(..., min_length=1)
    operations: List[TransformationOperation] = []
    references: List[str] = []
    preferences: Dict[str, Any] = {}
    preserve_identity: bool = True
    preserve_background: bool = False
    strength: float = 0.8


class TransformationResponse(BaseModel):
    id: str
    project_id: str
    source_asset_id: str
    status: str
    plan: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        extra = 'ignore'


class TransformationStatusResponse(BaseModel):
    id: str
    status: str
    progress: float = 0.0
    current_stage: Optional[str] = None
    error: Optional[str] = None
    result_asset_id: Optional[str] = None
    job_id: Optional[str] = None

    class Config:
        from_attributes = True
        extra = 'ignore'


class BatchTransformationRequest(BaseModel):
    project_id: str
    source_asset_ids: List[str]
    prompt: str = Field(..., min_length=1)
    operations: List[TransformationOperation] = []
    references: List[str] = []
    preferences: Dict[str, Any] = {}
    preserve_identity: bool = True
    preserve_background: bool = False
    strength: float = 0.8


class MaskRequest(BaseModel):
    asset_id: str
    mask_type: str
    frame_range: Optional[Dict[str, int]] = None
    feather: int = 5
    expand: int = 0
    invert: bool = False
    parameters: Dict[str, Any] = {}


class MaskResponse(BaseModel):
    id: str
    asset_id: str
    mask_type: str
    frames: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
        extra = 'ignore'


class TransformationAnalyzeResponse(BaseModel):
    suggested_operations: List[TransformationOperation]
    confidence: float
    requires_clarification: bool
    clarification_questions: List[str] = []
    missing_capabilities: List[str] = []
    warnings: List[str] = []
