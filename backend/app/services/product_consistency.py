from typing import Optional, Dict, Any, List
from app.schemas.phase7 import ProductConsistencyResult
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class ProductConsistencyService:
    @staticmethod
    async def lock_product_identity(
        project_id: str,
        asset_id: str,
        reference_asset_ids: List[str],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lock_id = f"product_lock:{project_id}:{asset_id}"
        lock_data = {
            "project_id": project_id,
            "asset_id": asset_id,
            "reference_asset_ids": reference_asset_ids,
            "constraints": constraints or {},
            "locked": True,
        }
        if redis_service.is_connected():
            await redis_service.set_json(lock_id, lock_data, ex=86400)
        return {
            "lock_id": lock_id,
            "asset_id": asset_id,
            "reference_asset_ids": reference_asset_ids,
            "constraints": constraints or {},
        }

    @staticmethod
    async def validate_product_consistency(
        asset_id: str,
        reference_asset_ids: List[str],
        result_metadata: Dict[str, Any],
    ) -> ProductConsistencyResult:
        if not reference_asset_ids:
            return ProductConsistencyResult(consistency_score=1.0, drift_detected=False, issues=[])

        issues = []
        scores = []

        color_dev = result_metadata.get("color_deviation", 0)
        color_score = max(0.0, 1.0 - color_dev)
        scores.append(("color", color_score))
        if color_dev > 0.15:
            issues.append(f"Product color deviation too high ({color_dev:.2f}).")

        geometry_score = result_metadata.get("geometry_score", 1.0)
        scores.append(("geometry", geometry_score))
        if geometry_score < 0.8:
            issues.append(f"Product geometry mismatch detected (score: {geometry_score:.2f}).")

        logo_detected = result_metadata.get("logo_detected", True)
        logo_score = 1.0 if logo_detected else 0.0
        scores.append(("logo", logo_score))
        if not logo_detected:
            issues.append("Product logo not detected in result.")

        avg_score = sum(s for _, s in scores) / max(len(scores), 1)
        return ProductConsistencyResult(
            consistency_score=avg_score,
            drift_detected=len(issues) > 0,
            issues=issues,
            geometry_match=geometry_score,
            color_match=color_score,
            logo_match=logo_score,
        )

    @staticmethod
    async def release_lock(lock_id: str) -> bool:
        if redis_service.is_connected():
            return await redis_service.delete(lock_id)
        return True

    @staticmethod
    async def get_lock(lock_id: str) -> Optional[Dict[str, Any]]:
        if redis_service.is_connected():
            return await redis_service.get_json(lock_id)
        return None
