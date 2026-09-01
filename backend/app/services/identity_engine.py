import uuid
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import (
    IdentityConsistencyResult,
    IdentityMode,
)
from app.services.redis_service import redis_service
from app.services.visual_analyzer import VisualAnalyzer
import logging

logger = logging.getLogger(__name__)


class IdentityEngine:
    @staticmethod
    async def create_identity_lock(
        project_id: str,
        asset_id: str,
        identity_type: str,
        reference_asset_ids: List[str],
        mode: str = "balanced",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lock_id = f"identity_lock:{project_id}:{asset_id}:{identity_type}"
        lock_data = {
            "project_id": project_id,
            "asset_id": asset_id,
            "identity_type": identity_type,
            "reference_asset_ids": reference_asset_ids,
            "mode": mode,
            "constraints": constraints or {},
            "locked": True,
        }
        if redis_service.is_connected():
            await redis_service.set_json(lock_id, lock_data, ex=86400)
        return {
            "lock_id": lock_id,
            "identity_type": identity_type,
            "reference_asset_ids": reference_asset_ids,
            "mode": mode,
            "constraints": constraints or {},
        }

    @staticmethod
    async def verify_identity_preservation(
        asset_id: str,
        reference_asset_ids: List[str],
        result_metadata: Dict[str, Any],
        mode: str = "balanced",
    ) -> IdentityConsistencyResult:
        if not reference_asset_ids:
            return IdentityConsistencyResult(identity_score=1.0, drift_detected=False, issues=[], mode=mode)

        issues = []
        score = 1.0

        if mode == IdentityMode.STRICT:
            tolerance = 0.05
        elif mode == IdentityMode.BALANCED:
            tolerance = 0.15
        else:
            tolerance = 0.3

        if result_metadata.get("has_faces") is False and "face" in result_metadata.get("identity_type", ""):
            issues.append("Face identity may have drifted: no faces detected in result.")
            score -= 0.3

        color_dev = result_metadata.get("color_deviation", 0)
        if color_dev > tolerance:
            issues.append(f"Color deviation exceeds tolerance ({color_dev:.2f} > {tolerance}). Identity may have changed.")
            score -= 0.2

        resolution_ratio = result_metadata.get("resolution_ratio", 1.0)
        if resolution_ratio < 0.9:
            issues.append(f"Resolution changed significantly ({resolution_ratio:.2f}). Identity features may be degraded.")
            score -= 0.1

        identity_type = result_metadata.get("identity_type", "")
        if identity_type and "face" in identity_type:
            face_count = result_metadata.get("face_count", 0)
            if face_count == 0:
                issues.append("No faces detected in result while identity preservation was requested.")
                score -= 0.4
            elif face_count > 2:
                issues.append(f"Multiple faces detected ({face_count}). Identity may have duplicated.")
                score -= 0.1

        score = max(0.0, min(1.0, score))
        return IdentityConsistencyResult(
            identity_score=score,
            drift_detected=len(issues) > 0,
            issues=issues,
            mode=mode,
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
