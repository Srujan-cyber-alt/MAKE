from typing import Optional, Dict, Any, List
from app.schemas.phase7 import (
    QualityGateResult,
    QualityScore,
    QualityIssue,
    QualityThresholds,
)
from app.services.temporal_consistency import TemporalConsistencyValidator
from app.services.identity_engine import IdentityEngine
from app.services.product_consistency import ProductConsistencyService
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class QualityGates:
    DEFAULT_THRESHOLDS = QualityThresholds()

    @staticmethod
    async def evaluate(
        video_path: str,
        thresholds: Optional[QualityThresholds] = None,
        identity_mode: str = "balanced",
        identity_required: bool = False,
        product_required: bool = False,
        result_metadata: Optional[Dict[str, Any]] = None,
        reference_asset_ids: Optional[List[str]] = None,
    ) -> QualityGateResult:
        thresholds = thresholds or QualityGates.DEFAULT_THRESHOLDS
        result_metadata = result_metadata or {}
        issues: List[QualityIssue] = []
        scores = []

        temporal = await QualityGates._check_temporal(video_path, thresholds)
        scores.append(("temporal", temporal["score"]))
        issues.extend(temporal.get("issues", []))

        resolution = await QualityGates._check_resolution(video_path, thresholds)
        scores.append(("resolution", resolution["score"]))
        issues.extend(resolution.get("issues", []))

        corruption = await QualityGates._check_corruption(video_path, thresholds)
        scores.append(("corruption", corruption["score"]))
        issues.extend(corruption.get("issues", []))

        identity_score = 1.0
        if identity_required:
            identity = await QualityGates._check_identity(result_metadata, identity_mode, reference_asset_ids or [])
            identity_score = identity["score"]
            issues.extend(identity.get("issues", []))

        product_score = 1.0
        if product_required:
            product = await QualityGates._check_product(result_metadata, reference_asset_ids or [])
            product_score = product["score"]
            issues.extend(product.get("issues", []))

        artifact_score = await QualityGates._estimate_artifact_score(result_metadata)

        overall = QualityGates._compute_overall(scores, identity_score, product_score, artifact_score)
        passed = overall >= thresholds.min_temporal_score and len([i for i in issues if i.severity == "critical"]) == 0

        action = "pass"
        if not passed:
            action = "retry"
        if overall < 0.3:
            action = "fallback"

        return QualityGateResult(
            passed=passed,
            score=QualityScore(
                overall=overall,
                temporal=scores[0][1] if scores else 0.0,
                identity=identity_score,
                artifact=artifact_score,
                resolution=scores[1][1] if len(scores) > 1 else 0.0,
                corruption=scores[2][1] if len(scores) > 2 else 0.0,
            ),
            issues=issues,
            action=action,
        )

    @staticmethod
    async def _check_temporal(video_path: str, thresholds: QualityThresholds) -> Dict[str, Any]:
        issues = []
        try:
            validation = await TemporalConsistencyValidator.validate(video_path)
            score = validation.get("consistency_score", 0.0)
            if score < thresholds.min_temporal_score:
                issues.append(QualityIssue(
                    severity="high",
                    category="temporal",
                    description=f"Temporal consistency score {score:.2f} is below threshold {thresholds.min_temporal_score:.2f}.",
                    suggestion="Retry with stronger temporal guidance or use a different provider.",
                ))
            return {"score": score, "issues": issues}
        except Exception as e:
            issues.append(QualityIssue(severity="medium", category="temporal", description=f"Temporal validation failed: {e}"))
            return {"score": 0.5, "issues": issues}

    @staticmethod
    async def _check_resolution(video_path: str, thresholds: QualityThresholds) -> Dict[str, Any]:
        issues = []
        try:
            info = await video_processing_service.inspect_media(video_path)
            score = 1.0
            if info.width and info.height:
                if info.width < 512 or info.height < 288:
                    score = 0.5
                    issues.append(QualityIssue(severity="low", category="resolution", description="Output resolution is very low."))
            return {"score": score, "issues": issues}
        except Exception as e:
            issues.append(QualityIssue(severity="medium", category="resolution", description=f"Resolution check failed: {e}"))
            return {"score": 0.7, "issues": issues}

    @staticmethod
    async def _check_corruption(video_path: str, thresholds: QualityThresholds) -> Dict[str, Any]:
        issues = []
        score = 1.0
        try:
            info = await video_processing_service.inspect_media(video_path)
            if not info or not info.format_name:
                score = 0.3
                issues.append(QualityIssue(severity="critical", category="corruption", description="Output file appears corrupted or unreadable."))
        except Exception as e:
            score = 0.3
            issues.append(QualityIssue(severity="critical", category="corruption", description=f"Corruption check failed: {e}"))
        return {"score": score, "issues": issues}

    @staticmethod
    async def _check_identity(result_metadata: Dict[str, Any], mode: str, reference_asset_ids: List[str]) -> Dict[str, Any]:
        if not reference_asset_ids:
            return {"score": 1.0, "issues": []}
        result = await IdentityEngine.verify_identity_preservation(
            asset_id=result_metadata.get("asset_id", ""),
            reference_asset_ids=reference_asset_ids,
            result_metadata=result_metadata,
            mode=mode,
        )
        issues = [QualityIssue(severity="high", category="identity", description=issue) for issue in result.issues]
        return {"score": result.identity_score, "issues": issues}

    @staticmethod
    async def _check_product(result_metadata: Dict[str, Any], reference_asset_ids: List[str]) -> Dict[str, Any]:
        if not reference_asset_ids:
            return {"score": 1.0, "issues": []}
        result = await ProductConsistencyService.validate_product_consistency(
            asset_id=result_metadata.get("asset_id", ""),
            reference_asset_ids=reference_asset_ids,
            result_metadata=result_metadata,
        )
        issues = [QualityIssue(severity="medium", category="product", description=issue) for issue in result.issues]
        return {"score": result.consistency_score, "issues": issues}

    @staticmethod
    async def _estimate_artifact_score(result_metadata: Dict[str, Any]) -> float:
        score = 1.0
        if result_metadata.get("has_artifacts"):
            score -= 0.3
        if result_metadata.get("flicker_detected"):
            score -= 0.2
        if result_metadata.get("black_frames_ratio", 0) > 0.05:
            score -= 0.2
        return max(0.0, min(1.0, score))

    @staticmethod
    def _compute_overall(scores: List[tuple], identity_score: float, product_score: float, artifact_score: float) -> float:
        all_scores = [s for _, s in scores] + [identity_score, product_score, artifact_score]
        return sum(all_scores) / max(len(all_scores), 1)
