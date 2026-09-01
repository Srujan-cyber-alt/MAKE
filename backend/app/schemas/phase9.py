from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class UserMode(str, Enum):
    AUTO = "auto"
    FAST = "fast"
    QUALITY = "quality"
    CINEMATIC = "cinematic"
    CHEAP = "cheap"


class ModelCapabilityDetail(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VIDEO_EXTENSION = "video_extension"
    FIRST_LAST_FRAME = "first_last_frame"
    REFERENCE_IMAGE = "reference_image"
    CHARACTER_CONSISTENCY = "character_consistency"
    PRODUCT_CONSISTENCY = "product_consistency"
    MOTION_TRANSFER = "motion_transfer"
    CAMERA_CONTROL = "camera_control"
    KEYFRAME_CONTROL = "keyframe_control"
    STYLE_TRANSFER = "style_transfer"
    INPAINTING = "inpainting"
    OUTPAINTING = "outpainting"
    UPSCALE = "upscale"
    FRAME_INTERPOLATION = "frame_interpolation"
    LIP_SYNC = "lip_sync"
    AUDIO_GENERATION = "audio_generation"
    IMAGE_GENERATION = "image_generation"


class CameraMovement(str, Enum):
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    ORBIT = "orbit"
    TRACKING = "tracking"
    HANDHELD = "handheld"
    CRANE = "crane"
    DRONE = "drone"
    WHIP_PAN = "whip_pan"
    RACK_FOCUS = "rack_focus"
    ZOOM = "zoom"


class ShotType(str, Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    BIRD_EYE = "bird_eye"
    LOW_ANGLE = "low_angle"
    DUTCH = "dutch"
    POV = "pov"


class LensType(str, Enum):
    WIDE = "wide"
    NORMAL = "normal"
    TELEPHOTO = "telephoto"
    MACRO = "macro"
    FISHEYE = "fisheye"
    ANAMORPHIC = "anamorphic"


class IdentityMode(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    CREATIVE = "creative"


class RepairType(str, Enum):
    IDENTITY = "identity"
    OBJECT = "object"
    BACKGROUND = "background"
    MOTION = "motion"
    LIGHTING = "lighting"
    TEMPORAL = "temporal"
    AUDIO = "audio"
    COMPOSITION = "composition"


class LookPreset(str, Enum):
    CINEMATIC = "cinematic"
    COMMERCIAL = "commercial"
    FILM = "film"
    DOCUMENTARY = "documentary"
    VINTAGE = "vintage"
    NEON = "neon"
    DARK = "dark"
    BRIGHT = "bright"
    WARM = "warm"
    COOL = "cool"


class PlatformPreset(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    INSTAGRAM_FEED = "instagram_feed"
    SHORTS = "shorts"
    CINEMA = "cinema"
    ADVERTISEMENT = "advertisement"


class GenerativeModelInfo(BaseModel):
    model_id: str
    provider_id: str
    name: str
    description: str
    capabilities: List[ModelCapabilityDetail] = []
    quality_score: float = 0.0
    speed_score: float = 0.0
    cost_score: float = 0.0
    max_duration_seconds: float = 4.0
    min_duration_seconds: float = 1.0
    supported_resolutions: List[str] = ["1920x1080"]
    supported_aspect_ratios: List[str] = ["16:9"]
    max_reference_images: int = 0
    input_types: List[str] = []
    output_types: List[str] = []
    temporal_consistency: bool = False
    identity_capability: bool = False
    motion_capability: bool = False
    camera_control: bool = False
    audio_capability: bool = False
    v2v_capability: bool = False
    extension_capability: bool = False
    metadata: Dict[str, Any] = {}


class CinematicPromptCompilation(BaseModel):
    subject: Optional[str] = None
    action: Optional[str] = None
    environment: Optional[str] = None
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    wardrobe: Optional[str] = None
    props: List[str] = []
    character: Optional[str] = None
    product: Optional[str] = None
    camera: Optional[str] = None
    shot_type: Optional[str] = None
    lens: Optional[str] = None
    focus: Optional[str] = None
    depth_of_field: Optional[str] = None
    camera_movement: Optional[str] = None
    composition: Optional[str] = None
    lighting: Optional[str] = None
    color: Optional[str] = None
    materials: Optional[str] = None
    physics: Optional[str] = None
    motion: Optional[str] = None
    facial_expression: Optional[str] = None
    body_movement: Optional[str] = None
    background: Optional[str] = None
    atmosphere: Optional[str] = None
    style: Optional[str] = None
    pacing: Optional[str] = None
    transitions: Optional[str] = None
    audio: Optional[str] = None
    voice: Optional[str] = None
    music: Optional[str] = None
    sfx: List[str] = []
    continuity: List[str] = []
    negative_constraints: List[str] = []
    compiled_prompt: Optional[str] = None


class TemporalConsistencyReport(BaseModel):
    score: float = 0.0
    issues: List[str] = []
    affected_frames: List[int] = []
    severity: str = "low"
    recommended_fix: Optional[str] = None
    face_drift: bool = False
    identity_drift: bool = False
    clothing_drift: bool = False
    product_drift: bool = False
    logo_drift: bool = False
    object_disappearance: bool = False
    object_duplication: bool = False
    lighting_jump: bool = False
    background_jump: bool = False
    camera_discontinuity: bool = False
    temporal_flicker: bool = False


class IdentityProfile(BaseModel):
    profile_id: str
    entity_type: str
    name: str
    face_features: Dict[str, Any] = {}
    body_proportions: Dict[str, Any] = {}
    hair: Dict[str, Any] = {}
    clothing: Dict[str, Any] = {}
    colors: Dict[str, Any] = {}
    materials: Dict[str, Any] = {}
    logos: List[str] = []
    shape: Dict[str, Any] = {}
    texture: Dict[str, Any] = {}
    distinctive_features: List[str] = []
    reference_asset_ids: List[str] = []
    mode: str = "balanced"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CharacterDefinition(BaseModel):
    character_id: str
    name: str
    age_range: Optional[str] = None
    appearance: Dict[str, Any] = {}
    hair: Dict[str, Any] = {}
    face: Dict[str, Any] = {}
    body: Dict[str, Any] = {}
    clothing: Dict[str, Any] = {}
    accessories: List[str] = []
    personality: Optional[str] = None
    voice: Optional[str] = None
    movement: Dict[str, Any] = {}
    reference_images: List[str] = []
    identity_profile_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductDefinition(BaseModel):
    product_id: str
    name: str
    shape: Dict[str, Any] = {}
    dimensions: Dict[str, Any] = {}
    materials: List[str] = []
    colors: Dict[str, Any] = {}
    logos: List[str] = []
    labels: List[str] = []
    packaging: Dict[str, Any] = {}
    brand_marks: List[str] = []
    orientation: Optional[str] = None
    surface_details: List[str] = []
    reference_images: List[str] = []
    identity_profile_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CameraDefinition(BaseModel):
    position: Dict[str, Any] = {}
    target: Dict[str, Any] = {}
    lens: Optional[str] = None
    fov: Optional[float] = None
    movement: Optional[str] = None
    speed: Optional[float] = None
    duration_seconds: Optional[float] = None
    easing: Optional[str] = None
    depth_of_field: Optional[str] = None
    aperture: Optional[str] = None
    focus_distance: Optional[float] = None
    shutter_feel: Optional[str] = None
    motion_blur: Optional[str] = None
    height: Optional[float] = None
    angle: Optional[str] = None


class MotionDefinition(BaseModel):
    action: str
    subject: Optional[str] = None
    object: Optional[str] = None
    intensity: float = 1.0
    duration_seconds: Optional[float] = None
    relationship: Optional[str] = None
    physically_plausible: bool = True


class KeyframeDefinition(BaseModel):
    parameter: str
    frame: int
    value: Any
    interpolation: str = "linear"
    easing: Optional[str] = None


class V2VWorkflowRequest(BaseModel):
    source_asset_id: str
    project_id: str
    prompt: str
    preserve_motion: bool = True
    preserve_composition: bool = True
    preserve_identity: bool = True
    preserve_timing: bool = True
    references: List[str] = []
    frame_range: Optional[Dict[str, int]] = None
    strength: float = 0.8
    guidance_scale: Optional[float] = None
    seed: Optional[int] = None


class ShotRepairRequest(BaseModel):
    shot_id: str
    repair_type: RepairType
    frame_range: Optional[Dict[str, int]] = None
    parameters: Dict[str, Any] = {}
    priority: str = "normal"


class UnifiedQualityScore(BaseModel):
    overall: float = 0.0
    visual: float = 0.0
    temporal: float = 0.0
    identity: float = 0.0
    motion: float = 0.0
    composition: float = 0.0
    audio: float = 0.0
    technical: float = 0.0
    issues: List[str] = []
    severity: str = "low"
    repair_recommendation: Optional[str] = None


class GenerationIteration(BaseModel):
    iteration_id: str
    project_id: str
    shot_id: Optional[str] = None
    parent_iteration_id: Optional[str] = None
    prompt: str
    compiled_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    references: List[str] = []
    seed: Optional[int] = None
    parameters: Dict[str, Any] = {}
    result_asset_id: Optional[str] = None
    quality_score: Optional[float] = None
    changes: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ColorLookAdjustment(BaseModel):
    preset: Optional[str] = None
    exposure: Optional[float] = None
    contrast: Optional[float] = None
    highlights: Optional[float] = None
    shadows: Optional[float] = None
    saturation: Optional[float] = None
    temperature: Optional[float] = None
    tint: Optional[float] = None
    grain: Optional[float] = None
    vignette: Optional[float] = None


class CaptionTrack(BaseModel):
    track_id: str
    language: str = "en"
    segments: List[Dict[str, Any]] = []
    style: Dict[str, Any] = {}
    burn_in: bool = False


class AudioTrack(BaseModel):
    track_id: str
    track_type: str
    source: Optional[str] = None
    volume: float = 1.0
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    ducking: bool = False
    parameters: Dict[str, Any] = {}


class GenerationJobGraph(BaseModel):
    graph_id: str
    project_id: str
    shots: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, str]] = []
    status: str = "pending"
    current_shot: Optional[str] = None
    cancelled: bool = False
    budget_guard: Optional[Dict[str, Any]] = None


class CostTracking(BaseModel):
    provider: str
    model: str
    generation_time_seconds: float
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    retries: int = 0
    failed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
