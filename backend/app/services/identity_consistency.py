from typing import List, Dict, Any, Optional
from app.services.redis_service import redis_service


class IdentityConsistencyService:

    @staticmethod
    async def lock_identity(
        project_id: str,
        asset_id: str,
        identity_type: str,
        reference_asset_ids: List[str],
        constraints: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        constraints = constraints or {}
        lock_id = f"identity_lock:{project_id}:{asset_id}:{identity_type}"

        lock_data = {
            "project_id": project_id,
            "asset_id": asset_id,
            "identity_type": identity_type,
            "reference_asset_ids": reference_asset_ids,
            "constraints": constraints,
            "locked": True,
        }

        if redis_service.is_connected():
            await redis_service.set_json(lock_id, lock_data, ex=86400)

        return {
            "lock_id": lock_id,
            "identity_type": identity_type,
            "reference_asset_ids": reference_asset_ids,
            "constraints": constraints,
        }

    @staticmethod
    async def check_identity_drift(
        asset_id: str,
        reference_asset_ids: List[str],
        result_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        drift_issues = []
        score = 1.0

        if not reference_asset_ids:
            return {"drift_detected": False, "score": score, "issues": []}

        result_resolution = result_metadata.get("resolution")
        reference_count = len(reference_asset_ids)

        if result_resolution and reference_count > 0:
            score -= 0.05 * reference_count

        if result_metadata.get("has_faces") is False and "face" in result_metadata.get("identity_type", ""):
            drift_issues.append("Face identity may have drifted: no faces detected in result.")
            score -= 0.3

        if result_metadata.get("color_deviation", 0) > 0.2:
            drift_issues.append("Color deviation exceeds threshold. Product/character color may have changed.")
            score -= 0.2

        score = max(0.0, min(1.0, score))

        return {
            "drift_detected": len(drift_issues) > 0,
            "score": score,
            "issues": drift_issues,
        }

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
