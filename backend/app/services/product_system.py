from typing import Optional, List, Dict, Any
from app.schemas.phase9 import ProductDefinition
from app.services.identity_lock_v2 import IdentityLockV2
import uuid
import logging

logger = logging.getLogger(__name__)


class ProductSystem:
    @staticmethod
    async def create_product(
        name: str,
        shape: Optional[Dict[str, Any]] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        materials: Optional[List[str]] = None,
        colors: Optional[Dict[str, Any]] = None,
        logos: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        packaging: Optional[Dict[str, Any]] = None,
        brand_marks: Optional[List[str]] = None,
        orientation: Optional[str] = None,
        surface_details: Optional[List[str]] = None,
        reference_images: Optional[List[str]] = None,
    ) -> ProductDefinition:
        product_id = str(uuid.uuid4())
        identity_profile = await IdentityLockV2.create_profile(
            entity_type="product",
            name=name,
            reference_asset_ids=reference_images or [],
            mode="strict",
            attributes={
                "shape": shape or {},
                "dimensions": dimensions or {},
                "materials": {"types": materials or []},
                "colors": colors or {},
                "logos": logos or [],
                "labels": labels or [],
                "packaging": packaging or {},
                "brand_marks": brand_marks or [],
                "orientation": orientation,
                "surface_details": surface_details or [],
            },
        )
        profile_id = identity_profile.profile_id

        product = ProductDefinition(
            product_id=product_id,
            name=name,
            shape=shape or {},
            dimensions=dimensions or {},
            materials=materials or [],
            colors=colors or {},
            logos=logos or [],
            labels=labels or [],
            packaging=packaging or {},
            brand_marks=brand_marks or [],
            orientation=orientation,
            surface_details=surface_details or [],
            reference_images=reference_images or [],
            identity_profile_id=profile_id,
        )

        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"product:{product_id}", product.model_dump(), ex=86400)

        logger.info(f"Created product {product_id}: {name}")
        return product

    @staticmethod
    async def get_product(product_id: str) -> Optional[Dict[str, Any]]:
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            return await redis_service.get_json(f"product:{product_id}")
        return None

    @staticmethod
    async def validate_product_consistency_v2(
        product_id: str,
        result_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        product_data = await ProductSystem.get_product(product_id)
        if not product_data:
            return {"score": 1.0, "drift_detected": False, "issues": []}

        issues = []
        score = 1.0
        tolerance = 0.1

        color_dev = result_metadata.get("color_deviation", 0)
        if color_dev > tolerance:
            issues.append(f"Product color deviation {color_dev:.2f} exceeds tolerance")
            score -= 0.3

        geometry_score = result_metadata.get("geometry_score", 1.0)
        if geometry_score < 0.8:
            issues.append(f"Product geometry score {geometry_score:.2f} below threshold")
            score -= 0.3

        logo_detected = result_metadata.get("logo_detected", True)
        if not logo_detected:
            issues.append("Product logo not detected in result")
            score -= 0.2

        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "drift_detected": len(issues) > 0,
            "issues": issues,
        }


def redis_service_is_connected():
    try:
        from app.services.redis_service import redis_service
        return redis_service.is_connected()
    except Exception:
        return False
