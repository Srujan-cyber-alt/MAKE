from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ComparisonMode(str, Enum):
    SIDE_BY_SIDE = "side_by_side"
    SPLIT_SLIDER = "split_slider"
    TOGGLE = "toggle"
    OVERLAY = "overlay"


class AudioAnalysisResult(BaseModel):
    has_audio: bool
    audio_codec: Optional[str] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    analysis: Dict[str, Any] = {}
    note: Optional[str] = None


class SpeechSegment(BaseModel):
    start: float
    end: float
    text: str
    confidence: float = 0.0


class SocialExportPreset(BaseModel):
    platform: str
    aspect_ratio: str
    resolution: str
    fps: int
    max_duration: int


class Keyframe(BaseModel):
    parameter: str
    frame: int
    value: Any
    interpolation: str = "linear"


class VFXLayerSequence(BaseModel):
    layers: List[Dict[str, Any]] = []
    total_duration: Optional[float] = None
    frame_range: Optional[Dict[str, int]] = None


class TrendToVideoRequest(BaseModel):
    project_id: str
    prompt: str
    duration_seconds: int = 15
    platform: str = "tiktok"
    style: Optional[str] = None
    references: List[str] = []


class AssetRequirement(BaseModel):
    asset_type: str
    required: bool
    description: str
    uploaded: bool = False
    asset_id: Optional[str] = None


class TrendToVideoResponse(BaseModel):
    concept: str
    script: List[Dict[str, Any]] = []
    shot_list: List[Dict[str, Any]] = []
    asset_requirements: List[AssetRequirement] = []
    missing_assets: List[str] = []
    ready_to_generate: bool = False
    message: str
