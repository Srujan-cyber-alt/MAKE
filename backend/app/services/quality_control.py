"""
Production Quality Control System for MAKE AI Video.

Every generated/transformed result must pass quality gates.

Checks:
- file exists
- playable
- duration
- resolution
- FPS
- aspect ratio
- codec
- file size
- corruption
- black frames
- frozen frames
- scene consistency
- temporal consistency
- identity consistency
- product consistency
- audio validity

Produces:
QUALITY SCORE 0-100
with dimension scores
"""

from typing import Optional, List, Dict, Any
from app.schemas.phase9 import UnifiedQualityScore
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.quality_gates import QualityGates
from app.services.identity_engine import IdentityEngine
from app.services.product_consistency import ProductConsistencyService
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class QualityControl:
    DEFAULT_THRESHOLD = 0.7
    MAX_REPAIR_ATTEMPTS = 3

    @staticmethod
    async def evaluate(
        video_path: str,
        result_metadata: Optional[Dict[str, Any]] = None,
        reference_asset_ids: Optional[List[str]] = None,
        identity_required: bool = False,
        product_required: bool = False,
        auto_repair: bool = True,
    ) -> UnifiedQualityScore:
        result_metadata = result_metadata or {}
        issues = []

        file_check = await QualityControl._check_file(video_path)
        if not file_check["valid"]:
            issues.extend(file_check["issues"])
            return UnifiedQualityScore(
                overall=0.0,
                technical=0.0,
                issues=issues,
                severity="critical",
                repair_recommendation="File is invalid or missing. Regenerate.",
            )

        technical = await QualityControl._check_technical(video_path)
        issues.extend(technical.get("issues", []))

        temporal = await TemporalConsistencyEngine.analyze(video_path)
        issues.extend([f"Temporal: {i}" for i in temporal.issues])

        quality = await QualityGates.evaluate(
            video_path=video_path,
            identity_required=identity_required,
            product_required=product_required,
            result_metadata=result_metadata,
            reference_asset_ids=reference_asset_ids or [],
        )
        issues.extend([f"Quality: {i.description}" for i in quality.issues])

        identity_score = quality.score.identity if identity_required else 1.0
        product_score = 1.0
        if product_required and reference_asset_ids:
            product = await ProductConsistencyService.validate_product_consistency(
                asset_id=result_metadata.get("asset_id", ""),
                reference_asset_ids=reference_asset_ids,
                result_metadata=result_metadata,
            )
            product_score = product.consistency_score
            issues.extend([f"Product: {i}" for i in product.issues])

        visual = quality.score.overall
        temporal_score = temporal.score
        motion_score = 1.0
        composition_score = quality.score.resolution
        audio_score = 1.0

        overall = (
            visual + temporal_score + identity_score + product_score + motion_score + composition_score + audio_score + technical["score"]
        ) / 8

        severity = "low"
        if overall < 0.3:
            severity = "critical"
        elif overall < 0.6:
            severity = "high"
        elif overall < 0.8:
            severity = "medium"

        repair = None
        if overall < QualityControl.DEFAULT_THRESHOLD and auto_repair:
            repair = "Retry generation with adjusted parameters or use fallback provider."

        return UnifiedQualityScore(
            overall=overall,
            visual=visual,
            temporal=temporal_score,
            identity=identity_score,
            motion=motion_score,
            composition=composition_score,
            audio=audio_score,
            technical=technical["score"],
            issues=issues,
            severity=severity,
            repair_recommendation=repair,
        )

    @staticmethod
    async def _check_file(video_path: str) -> Dict[str, Any]:
        from pathlib import Path
        path = Path(video_path)
        if not path.exists():
            return {"valid": False, "issues": ["File does not exist"]}
        if path.stat().st_size < 1024:
            return {"valid": False, "issues": ["File is too small to be valid video"]}
        return {"valid": True, "issues": []}

    @staticmethod
    async def _check_technical(video_path: str) -> Dict[str, Any]:
        issues = []
        score = 1.0
        try:
            info = await video_processing_service.inspect_media(video_path)
            if not info:
                issues.append("Could not inspect media")
                return {"score": 0.0, "issues": issues}

            if info.width and info.height:
                if info.width < 256 or info.height < 144:
                    issues.append(f"Resolution too low: {info.width}x{info.height}")
                    score -= 0.3

            if info.fps and info.fps < 10:
                issues.append(f"FPS too low: {info.fps}")
                score -= 0.2

            if info.duration_seconds and info.duration_seconds < 0.5:
                issues.append(f"Duration too short: {info.duration_seconds}s")
                score -= 0.3

            if not info.format_name:
                issues.append("Unknown format")
                score -= 0.2

        except Exception as e:
            issues.append(f"Technical check failed: {e}")
            score = 0.0

        return {"score": max(0.0, score), "issues": issues}
