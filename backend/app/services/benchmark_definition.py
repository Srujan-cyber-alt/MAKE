"""
Model Lab Benchmark Definition for MAKE AI Video Phase 20.

Extends Phase 16 ModelBenchmark with structured benchmark definitions,
deterministic test cases, and controlled experiment support.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class BenchmarkTaskType:
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VIDEO_EXTENSION = "video_extension"
    CHARACTER = "character"
    PRODUCT = "product"
    ENVIRONMENT = "environment"
    CAMERA = "camera"
    MOTION = "motion"
    CINEMATIC = "cinematic"
    CONTINUITY = "continuity"
    VFX = "vfx"
    EDITING = "editing"
    AUDIO = "audio"
    SOCIAL_VIDEO = "social_video"


class BenchmarkStatus:
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkCase:
    @staticmethod
    def create(task_type: str, prompt: str, negative_prompt: str = "", reference_assets: List[str] = None, duration: float = 5.0, aspect_ratio: str = "16:9", resolution: str = "1920x1080", camera: Dict[str, Any] = None, motion: Dict[str, Any] = None, style: str = "cinematic", identity_requirements: List[str] = None, product_requirements: List[str] = None, continuity_requirements: List[str] = None, quality_target: float = 0.7, expected_behavior: str = "") -> Dict[str, Any]:
        return {
            "case_id": str(uuid.uuid4()),
            "task_type": task_type,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "reference_assets": reference_assets or [],
            "duration_seconds": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "camera": camera or {},
            "motion": motion or {},
            "style": style,
            "identity_requirements": identity_requirements or [],
            "product_requirements": product_requirements or [],
            "continuity_requirements": continuity_requirements or [],
            "quality_target": quality_target,
            "expected_behavior": expected_behavior,
        }

    @staticmethod
    def get_standard_cases() -> List[Dict[str, Any]]:
        return [
            BenchmarkCase.create(BenchmarkTaskType.CINEMATIC, "cinematic product hero shot, luxury watch, macro, studio lighting", style="luxury", quality_target=0.8),
            BenchmarkCase.create(BenchmarkTaskType.CHARACTER, "a person walking toward camera, confident stride, urban street", style="cinematic", quality_target=0.75),
            BenchmarkCase.create(BenchmarkTaskType.CAMERA, "slow dolly-in, medium shot, smooth movement, cinematic", camera={"movement": "dolly", "speed": 0.3}, quality_target=0.7),
            BenchmarkCase.create(BenchmarkTaskType.MOTION, "fast camera movement, action, dynamic motion, energetic", motion={"action": "fast_movement", "intensity": 0.9}, quality_target=0.7),
            BenchmarkCase.create(BenchmarkTaskType.PRODUCT, "product macro shot, detailed, close-up, premium lighting", style="product", quality_target=0.8),
            BenchmarkCase.create(BenchmarkTaskType.CHARACTER, "character close-up, emotional performance, shallow depth of field", style="cinematic", quality_target=0.75),
            BenchmarkCase.create(BenchmarkTaskType.ENVIRONMENT, "complex environment, detailed cityscape, atmospheric, night rain", style="cinematic", quality_target=0.7),
            BenchmarkCase.create(BenchmarkTaskType.CINEMATIC, "night rain neon environment, wet surfaces, reflections, cyberpunk", style="cinematic", quality_target=0.75),
            BenchmarkCase.create(BenchmarkTaskType.TEXT_TO_VIDEO, "simple text to video, clean background, product showcase", style="commercial", quality_target=0.7),
            BenchmarkCase.create(BenchmarkTaskType.SOCIAL_VIDEO, "short form vertical video, dynamic, fast cuts, social media optimized", aspect_ratio="9:16", duration=15.0, quality_target=0.7),
        ]


class BenchmarkDefinition:
    @staticmethod
    def create(name: str, description: str, task_type: str, cases: List[Dict[str, Any]], models: List[str], providers: List[str], evaluation_policy: Dict[str, Any] = None, created_by: str = "system") -> Dict[str, Any]:
        return {
            "benchmark_id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "task_type": task_type,
            "cases": cases,
            "models": models,
            "providers": providers,
            "evaluation_policy": evaluation_policy or {
                "min_technical_score": 0.7,
                "min_quality_score": 0.6,
                "max_repair_attempts": 2,
                "auto_accept_threshold": 0.85,
            },
            "status": BenchmarkStatus.CREATED,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "dataset_version": "1.0",
            "test_case_count": len(cases),
        }


benchmark_definition = BenchmarkDefinition()
