from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MLBackendStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    GPU_REQUIRED = "gpu_required"
    NOT_INSTALLED = "not_installed"


class TargetCategory(str, Enum):
    PERSON = "person"
    FACE = "face"
    OBJECT = "object"
    PRODUCT = "product"
    VEHICLE = "vehicle"
    BACKGROUND = "background"
    SKY = "sky"
    TEXT = "text"
    LOGO = "logo"
    CLOTHING = "clothing"
    ANIMAL = "animal"
    CUSTOM = "custom"


class SegmentationModel(str, Enum):
    SAM = "sam"
    SAM2 = "sam2"
    YOLO = "yolo"
    YOLO_WORLD = "yolo_world"
    GROUNDING_DINO = "grounding_dino"
    REMBG = "rembg"
    CUSTOM = "custom"


class TrackingModel(str, Enum):
    SORT = "sort"
    DEEP_SORT = "deep_sort"
    BYTE_TRACK = "byte_track"
    BOTSORT = "botsort"
    STRONGSORT = "strongsort"
    MEDIAN_FLOW = "median_flow"
    CUSTOM = "custom"


class IdentityMode(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    CREATIVE = "creative"


class QualityThresholds(BaseModel):
    min_temporal_score: float = 0.7
    min_identity_score: float = 0.8
    min_artifact_score: float = 0.3
    max_black_frames_ratio: float = 0.05
    max_missing_frames_ratio: float = 0.02
    min_resolution_match: float = 0.9
    max_corruption_indicators: int = 0


class VideoAnalysis(BaseModel):
    duration_seconds: Optional[float] = None
    resolution: Optional[Tuple[int, int]] = None
    fps: Optional[float] = None
    aspect_ratio: Optional[str] = None
    codec: Optional[str] = None
    scene_changes: List[float] = []
    key_frames: List[Dict[str, Any]] = []
    motion_vectors: List[Dict[str, Any]] = []
    ml_available: Dict[str, MLBackendStatus] = {}
    audio_codec: Optional[str] = None
    file_size_bytes: Optional[int] = None


class DetectedTarget(BaseModel):
    target_id: str
    category: TargetCategory
    label: str
    confidence: float
    bbox: Optional[Dict[str, Any]] = None
    frame_range: Optional[Dict[str, int]] = None
    attributes: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    color_histogram: Optional[List[float]] = None


class SegmentationResult(BaseModel):
    mask_id: str
    target_id: str
    type: str
    confidence: float
    bbox: Optional[Dict[str, Any]] = None
    frame_number: Optional[int] = None
    mask_path: Optional[str] = None
    parameters: Dict[str, Any] = {}
    model: Optional[str] = None
    generated_by: str


class TrackingResult(BaseModel):
    track_id: str
    target_id: str
    object_type: str
    bbox: Dict[str, Any]
    confidence: float
    frame_range: Dict[str, int]
    occlusion_count: int = 0
    visibility_ratio: float = 1.0
    tracks: List[Dict[str, Any]] = []


class FrameExtractionResult(BaseModel):
    frame_paths: List[str]
    timestamps: List[float]
    count: int
    resolution: Optional[Tuple[int, int]] = None
    format: str = "png"


class IdentityConsistencyResult(BaseModel):
    identity_score: float
    drift_detected: bool
    issues: List[str] = []
    reference_matches: List[Dict[str, Any]] = []
    mode: str = "balanced"


class ProductConsistencyResult(BaseModel):
    consistency_score: float
    drift_detected: bool
    issues: List[str] = []
    geometry_match: Optional[float] = None
    color_match: Optional[float] = None
    logo_match: Optional[float] = None


class VisualAnalyzerResponse(BaseModel):
    analysis: VideoAnalysis
    objects: List[DetectedTarget] = []
    faces: List[DetectedTarget] = []
    scenes: List[Dict[str, Any]] = []
    motion: Dict[str, Any] = {}
    ml_available: Dict[str, bool] = {}
    ambiguity: Optional[Dict[str, Any]] = None


class TargetMatch(BaseModel):
    target_id: str
    category: TargetCategory
    label: str
    confidence: float
    is_ambiguous: bool = False
    alternatives: List[str] = []


class SmartTargetSelection(BaseModel):
    matches: List[TargetMatch]
    primary_target: Optional[TargetMatch] = None
    requires_clarification: bool = False
    clarification_options: List[Dict[str, Any]] = []


class FrameRange(BaseModel):
    start_frame: Optional[int] = None
    end_frame: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    scene_index: Optional[int] = None
    shot_index: Optional[int] = None
    all_frames: bool = False

    def to_frame_range_dict(self) -> Dict[str, int]:
        if self.all_frames:
            return {}
        result = {}
        if self.start_frame is not None:
            result["start"] = self.start_frame
        if self.end_frame is not None:
            result["end"] = self.end_frame
        return result

    def to_time_range_dict(self) -> Dict[str, float]:
        if self.all_frames:
            return {}
        result = {}
        if self.start_time is not None:
            result["start"] = self.start_time
        if self.end_time is not None:
            result["end"] = self.end_time
        return result


class QualityIssue(BaseModel):
    severity: str
    category: str
    description: str
    frame_range: Optional[Dict[str, int]] = None
    suggestion: Optional[str] = None


class QualityScore(BaseModel):
    overall: float
    temporal: float
    identity: float
    artifact: float
    resolution: float
    corruption: float


class QualityGateResult(BaseModel):
    passed: bool
    score: QualityScore
    issues: List[QualityIssue] = []
    action: str = "pass"
    retry_count: int = 0
    fallback_used: bool = False


class JobGraphNode(BaseModel):
    node_id: str
    job_type: str
    status: str = "pending"
    progress: float = 0.0
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    dependencies: List[str] = []
    retry_count: int = 0
    error: Optional[str] = None
    timestamps: Dict[str, Optional[str]] = {}


class JobGraph(BaseModel):
    graph_id: str
    transformation_id: str
    nodes: List[JobGraphNode] = []
    edges: List[Dict[str, str]] = []
    status: str = "pending"
    current_node: Optional[str] = None
    cancelled: bool = False


class VersionSnapshot(BaseModel):
    version_id: str
    project_id: str
    parent_version_id: Optional[str] = None
    version_number: int
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: str
    operations: List[Dict[str, Any]] = []
    asset_ids: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PromptIterationHistory(BaseModel):
    iteration_id: str
    project_id: str
    base_version_id: Optional[str] = None
    prompt: str
    operations: List[Dict[str, Any]] = []
    result_asset_id: Optional[str] = None
    quality_score: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MLModelRegistryEntry(BaseModel):
    model_id: str
    model_type: str
    name: str
    version: str
    path: Optional[str] = None
    capabilities: List[str] = []
    memory_requirement_mb: Optional[int] = None
    gpu_required: bool = False
    installed: bool = False
    metadata: Dict[str, Any] = {}


class ObjectRemovalProvenance(BaseModel):
    source_asset_id: str
    target_asset_id: str
    mask_id: str
    frame_range: Dict[str, int]
    method: str
    output_path: str
    validation: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BackgroundReplacementParams(BaseModel):
    background_prompt: Optional[str] = None
    background_image_id: Optional[str] = None
    lighting_match: bool = True
    color_match: bool = True
    depth_aware: bool = False
    edge_refinement: bool = True
    shadow_handling: bool = True
    temporal_consistency: bool = True


class MotionTransferParams(BaseModel):
    reference_video_id: Optional[str] = None
    motion_strength: float = 0.8
    preserve_identity: bool = True
    temporal_smoothing: bool = True
    frame_range: Optional[Dict[str, int]] = None


class V2VTransformParams(BaseModel):
    style_prompt: str
    preserve_identity: bool = True
    preserve_composition: bool = True
    preserve_camera: bool = True
    preserve_timing: bool = True
    strength: float = 0.8
    guidance_scale: Optional[float] = None
    seed: Optional[int] = None
    frame_range: Optional[Dict[str, int]] = None
