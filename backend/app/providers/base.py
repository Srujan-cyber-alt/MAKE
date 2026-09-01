from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ProviderCapability(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VIDEO_EDITING = "video_editing"
    UPSCALING = "upscaling"
    MOTION_GENERATION = "motion_generation"
    FACE_ANIMATION = "face_animation"
    OBJECT_REMOVAL = "object_removal"
    BACKGROUND_REPLACEMENT = "background_replacement"
    IMAGE_GENERATION = "image_generation"


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
    async def submit_generation(self, request: GenerationRequest) -> GenerationResponse:
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
    def get_capabilities(self) -> List[ProviderCapability]:
        raise NotImplementedError

    @abstractmethod
    def get_supported_models(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class ProviderRegistry:
    _providers: Dict[str, VideoProviderAdapter] = {}

    @classmethod
    def register(cls, provider: VideoProviderAdapter):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[VideoProviderAdapter]:
        return cls._providers.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, VideoProviderAdapter]:
        return dict(cls._providers)

    @classmethod
    def get_by_capability(cls, capability: ProviderCapability) -> List[VideoProviderAdapter]:
        return [p for p in cls._providers.values() if capability in p.get_capabilities()]
