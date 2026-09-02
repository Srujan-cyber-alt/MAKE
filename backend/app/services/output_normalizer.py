"""
Output Normalizer for MAKE AI Video Phase 16.

Normalizes provider-specific output into MAKE's canonical result format.
"""

from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from app.services.result_validator import ResultValidator

logger = logging.getLogger(__name__)


@dataclass
class CanonicalGenerationResult:
    job_id: str
    provider: str
    model: str
    model_version: str
    status: str
    output_asset: Optional[str] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[Tuple[int, int]] = None
    fps: Optional[int] = None
    aspect_ratio: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    provider_metadata: Dict[str, Any] = field(default_factory=dict)
    cost: Optional[float] = None
    generation_time: Optional[float] = None
    validation: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class OutputNormalizer:
    def __init__(self):
        self.validator = ResultValidator()

    def normalize(self, provider_response: Any, provider_name: str, model_id: str, job_id: str, start_time: datetime = None) -> CanonicalGenerationResult:
        start_time = start_time or datetime.utcnow()
        generation_time = (datetime.utcnow() - start_time).total_seconds()

        if hasattr(provider_response, 'video_url'):
            video_url = provider_response.video_url
            duration = provider_response.duration_seconds
            width = provider_response.width
            height = provider_response.height
            fps = provider_response.fps
            metadata = provider_response.metadata or {}
            status = provider_response.status
            provider_job_id = provider_response.provider_job_id
        elif isinstance(provider_response, dict):
            video_url = provider_response.get("video_url") or provider_response.get("output_url")
            duration = provider_response.get("duration_seconds") or provider_response.get("duration")
            width = provider_response.get("width")
            height = provider_response.get("height")
            fps = provider_response.get("fps")
            metadata = provider_response.get("metadata", {})
            status = provider_response.get("status", "unknown")
            provider_job_id = provider_response.get("provider_job_id", job_id)
        else:
            video_url = None
            duration = None
            width = None
            height = None
            fps = None
            metadata = {}
            status = "unknown"
            provider_job_id = job_id

        aspect_ratio = None
        if width and height:
            from math import gcd
            g = gcd(width, height)
            aspect_ratio = f"{width // g}:{height // g}"

        validation = {}
        if video_url:
            validation = self.validator.validate_output(video_url, duration, width, height).__dict__ if hasattr(self.validator.validate_output(video_url, duration, width, height), '__dict__') else {}

        return CanonicalGenerationResult(
            job_id=job_id,
            provider=provider_name,
            model=model_id,
            model_version=metadata.get("model_version", "1.0"),
            status=status,
            output_asset=video_url,
            duration_seconds=duration,
            resolution=(width, height) if width and height else None,
            fps=fps,
            aspect_ratio=aspect_ratio,
            provenance={
                "provider": provider_name,
                "model": model_id,
                "provider_job_id": provider_job_id,
                "request_timestamp": start_time.isoformat(),
                "response_timestamp": datetime.utcnow().isoformat(),
            },
            provider_metadata=metadata,
            cost=provider_response.get("cost") if isinstance(provider_response, dict) else getattr(provider_response, 'cost', None),
            generation_time=generation_time,
            validation=validation,
            quality={},
            completed_at=datetime.utcnow(),
        )

    def to_dict(self, result: CanonicalGenerationResult) -> Dict[str, Any]:
        return {
            "job_id": result.job_id,
            "provider": result.provider,
            "model": result.model,
            "model_version": result.model_version,
            "status": result.status,
            "output_asset": result.output_asset,
            "duration_seconds": result.duration_seconds,
            "resolution": result.resolution,
            "fps": result.fps,
            "aspect_ratio": result.aspect_ratio,
            "provenance": result.provenance,
            "provider_metadata": result.provider_metadata,
            "cost": result.cost,
            "generation_time": result.generation_time,
            "validation": result.validation,
            "quality": result.quality,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }


output_normalizer = OutputNormalizer()
