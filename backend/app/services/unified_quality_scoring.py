from typing import Optional, List, Dict, Any
from app.schemas.phase9 import UnifiedQualityScore
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.quality_gates import QualityGates
from app.services.identity_engine import IdentityEngine
from app.services.product_consistency import ProductConsistencyService
import logging

logger = logging.getLogger(__name__)


class UnifiedQualityScoring:
    @staticmethod
    async def score(
        video_path: str,
        result_metadata: Optional[Dict[str, Any]] = None,
        reference_asset_ids: Optional[List[str]] = None,
        identity_required: bool = False,
        product_required: bool = False,
    ) -> UnifiedQualityScore:
        result_metadata = result_metadata or {}
        issues = []

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

        visual = quality.score.overall
        temporal_score = temporal.score
        identity_score = quality.score.identity if identity_required else 1.0
        motion_score = 1.0
        composition_score = quality.score.resolution
        audio_score = 1.0
        technical_score = quality.score.corruption

        overall = (visual + temporal_score + identity_score + motion_score + composition_score + audio_score + technical_score) / 7

        severity = "low"
        if overall < 0.3:
            severity = "critical"
        elif overall < 0.6:
            severity = "high"
        elif overall < 0.8:
            severity = "medium"

        repair = None
        if overall < 0.7:
            repair = "Retry generation with adjusted parameters or use fallback provider."

        return UnifiedQualityScore(
            overall=overall,
            visual=visual,
            temporal=temporal_score,
            identity=identity_score,
            motion=motion_score,
            composition=composition_score,
            audio=audio_score,
            technical=technical_score,
            issues=issues,
            severity=severity,
            repair_recommendation=repair,
        )
