from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ProviderCapability(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VIDEO_EDITING = "video_editing"
    TRIM = "trim"
    CUT = "cut"
    RESIZE = "resize"
    UPSCALING = "upscaling"
    MOTION_GENERATION = "motion_generation"
    FACE_ANIMATION = "face_animation"
    OBJECT_REMOVAL = "object_removal"
    BACKGROUND_REPLACEMENT = "background_replacement"
    IMAGE_GENERATION = "image_generation"
    VIDEO_EXTENSION = "video_extension"
    REFERENCE_IMAGES = "reference_images"
    MULTI_REFERENCE = "multi_reference"
    SEED_CONTROL = "seed_control"
    GUIDANCE_SCALE = "guidance_scale"
    ASPECT_RATIO = "aspect_ratio"
    CUSTOM_RESOLUTION = "custom_resolution"
    DURATION_CONTROL = "duration_control"
    SPEED_CHANGE = "speed_change"
    MUTE_AUDIO = "mute_audio"


@dataclass
class ModelLimits:
    max_duration_seconds: float = 4.0
    min_duration_seconds: float = 1.0
    max_width: int = 1920
    max_height: int = 1080
    supported_aspect_ratios: List[str] = field(default_factory=lambda: ["16:9"])
    max_input_images: int = 1
    max_reference_images: int = 0
    supports_seed: bool = False
    supports_negative_prompt: bool = False
    supports_guidance_scale: bool = False
    cost_per_second: Optional[float] = None


@dataclass
class ModelInfo:
    id: str
    name: str
    description: str
    capabilities: List[ProviderCapability]
    limits: ModelLimits
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationRequest:
    prompt: str
    negative_prompt: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    aspect_ratio: Optional[str] = None
    seed: Optional[int] = None
    guidance_scale: Optional[float] = None
    input_images: Optional[List[str]] = None
    input_video_url: Optional[str] = None
    reference_images: Optional[List[Dict[str, Any]]] = None
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class GenerationResponse:
    provider_job_id: str
    status: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    seed: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ProviderHealth:
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()


class VideoProviderAdapter(ABC):
    def __init__(self, name: str, api_base: str, api_key: Optional[str] = None):
        self.name = name
        self.api_base = api_base
        self.api_key = api_key

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    async def submit_generation(self, request: GenerationRequest, model_id: str) -> GenerationResponse:
        raise NotImplementedError

    @abstractmethod
    async def check_status(self, provider_job_id: str) -> GenerationResponse:
        raise NotImplementedError

    @abstractmethod
    async def cancel_job(self, provider_job_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, provider_job_id: str) -> Optional[GenerationResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> Set[ProviderCapability]:
        raise NotImplementedError

    @abstractmethod
    def get_supported_models(self) -> List[ModelInfo]:
        raise NotImplementedError

    def supports_capability(self, capability: ProviderCapability) -> bool:
        return capability in self.get_capabilities()


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, VideoProviderAdapter] = {}

    def register(self, provider: VideoProviderAdapter):
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[VideoProviderAdapter]:
        return self._providers.get(name)

    def get_all(self) -> Dict[str, VideoProviderAdapter]:
        return dict(self._providers)

    def get_by_capability(self, capability: ProviderCapability) -> List[VideoProviderAdapter]:
        return [p for p in self._providers.values() if capability in p.get_capabilities()]

    def get_provider_model(self, provider_name: str, model_id: str) -> Optional[ModelInfo]:
        provider = self.get(provider_name)
        if not provider:
            return None
        for model in provider.get_supported_models():
            if model.id == model_id:
                return model
        return None
