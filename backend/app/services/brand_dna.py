"""
Brand DNA Engine for MAKE AI Video.

Allows:
- logo
- colors
- fonts
- tone
- visual style
- photography style
- camera style
- music style
- language
- CTA rules
- product rules
- legal disclaimers

Every generation can optionally validate against Brand DNA.
"""

from typing import Optional, List, Dict, Any
from app.services.redis_service import redis_service
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class BrandDNA:
    @staticmethod
    async def create_brand_dna(
        user_id: str,
        name: str,
        logo: Optional[str] = None,
        colors: Optional[Dict[str, Any]] = None,
        fonts: Optional[List[str]] = None,
        tone: Optional[str] = None,
        visual_style: Optional[str] = None,
        photography_style: Optional[str] = None,
        camera_style: Optional[str] = None,
        music_style: Optional[str] = None,
        language: Optional[str] = None,
        cta_rules: Optional[List[str]] = None,
        product_rules: Optional[List[str]] = None,
        legal_disclaimers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        brand_id = f"brand:{uuid.uuid4()}"
        brand_data = {
            "brand_id": brand_id,
            "user_id": user_id,
            "name": name,
            "logo": logo,
            "colors": colors or {},
            "fonts": fonts or [],
            "tone": tone or "professional",
            "visual_style": visual_style or "clean modern",
            "photography_style": photography_style or "commercial",
            "camera_style": camera_style or "smooth cinematic",
            "music_style": music_style or "upbeat corporate",
            "language": language or "english",
            "cta_rules": cta_rules or ["keep it short", "include logo"],
            "product_rules": product_rules or ["product must be clearly visible", "logo must face camera"],
            "legal_disclaimers": legal_disclaimers or [],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if redis_service.is_connected():
            await redis_service.set_json(brand_id, brand_data, ex=86400 * 30)
        
        logger.info(f"Created brand DNA {brand_id}: {name}")
        return brand_data

    @staticmethod
    async def get_brand_dna(brand_id: str) -> Optional[Dict[str, Any]]:
        if redis_service.is_connected():
            return await redis_service.get_json(brand_id)
        return None

    @staticmethod
    async def validate_against_brand(brand_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        brand = await BrandDNA.get_brand_dna(brand_id)
        if not brand:
            return {"valid": True, "warnings": [], "errors": ["Brand DNA not found"]}
        
        issues = []
        warnings = []
        
        if brand.get("colors") and content.get("colors"):
            content_colors = content["colors"]
            for key, value in content_colors.items():
                if key in brand["colors"]:
                    if value != brand["colors"][key]:
                        warnings.append(f"Color {key} does not match brand standard")
        
        if brand.get("tone") and content.get("tone"):
            if content["tone"] != brand["tone"]:
                warnings.append(f"Tone '{content['tone']}' does not match brand tone '{brand['tone']}'")
        
        if brand.get("product_rules"):
            for rule in brand["product_rules"]:
                if rule.lower() in ["product must be clearly visible", "logo must face camera"]:
                    if not content.get("product_visible"):
                        warnings.append(f"Brand rule: {rule}")
        
        return {
            "valid": len(issues) == 0,
            "warnings": warnings,
            "errors": issues,
            "brand_compliance_score": max(0.0, 1.0 - (len(warnings) * 0.1) - (len(issues) * 0.3)),
        }

    @staticmethod
    async def list_brands(user_id: str) -> List[Dict[str, Any]]:
        brands = []
        if redis_service.is_connected():
            keys = await redis_service._client.keys("brand:*") if redis_service._client else []
            for key in keys:
                brand = await redis_service.get_json(key)
                if brand and brand.get("user_id") == user_id:
                    brands.append(brand)
        return brands
