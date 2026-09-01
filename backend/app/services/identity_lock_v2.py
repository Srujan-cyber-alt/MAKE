from typing import Optional, List, Dict, Any
from app.schemas.phase9 import IdentityProfile
from app.services.redis_service import redis_service
import uuid
import logging

logger = logging.getLogger(__name__)


class IdentityLockV2:
    @staticmethod
    async def create_profile(
        entity_type: str,
        name: str,
        reference_asset_ids: List[str],
        mode: str = "balanced",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> IdentityProfile:
        profile_id = str(uuid.uuid4())
        profile = IdentityProfile(
            profile_id=profile_id,
            entity_type=entity_type,
            name=name,
            reference_asset_ids=reference_asset_ids,
            mode=mode,
            **(attributes or {}),
        )

        if redis_service.is_connected():
            await redis_service.set_json(f"identity_profile:{profile_id}", profile.model_dump(), ex=86400)

        logger.info(f"Created identity profile {profile_id} for {entity_type} '{name}'")
        return profile

    @staticmethod
    async def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
        if redis_service.is_connected():
            return await redis_service.get_json(f"identity_profile:{profile_id}")
        return None

    @staticmethod
    async def update_profile(profile_id: str, updates: Dict[str, Any]) -> Optional[IdentityProfile]:
        profile_data = await IdentityLockV2.get_profile(profile_id)
        if not profile_data:
            return None
        profile_data.update(updates)
        profile = IdentityProfile(**profile_data)
        if redis_service.is_connected():
            await redis_service.set_json(f"identity_profile:{profile_id}", profile.model_dump(), ex=86400)
        return profile

    @staticmethod
    async def verify_identity(
        profile_id: str,
        result_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        profile_data = await IdentityLockV2.get_profile(profile_id)
        if not profile_data:
            return {"score": 1.0, "drift_detected": False, "issues": []}

        mode = profile_data.get("mode", "balanced")
        issues = []
        score = 1.0

        if mode == "strict":
            tolerance = 0.05
        elif mode == "balanced":
            tolerance = 0.15
        else:
            tolerance = 0.3

        color_dev = result_metadata.get("color_deviation", 0)
        if color_dev > tolerance:
            issues.append(f"Color deviation {color_dev:.2f} exceeds tolerance {tolerance:.2f}")
            score -= 0.2

        resolution_ratio = result_metadata.get("resolution_ratio", 1.0)
        if resolution_ratio < 0.9:
            issues.append(f"Resolution changed significantly ({resolution_ratio:.2f})")
            score -= 0.1

        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "drift_detected": len(issues) > 0,
            "issues": issues,
            "mode": mode,
        }
