"""
Asset Intelligence System for MAKE AI Video.

Intelligent asset library with automatic classification and semantic search.

Automatically classifies:
- people
- characters
- products
- locations
- logos
- styles
- videos
- audio
- music
- references

Supports semantic search:
"Show me all shots with the red sneaker."
"Find the woman from the previous campaign."
"Use the same location as scene 2."
"""

from typing import Optional, List, Dict, Any
from app.services.media_understanding import MediaUnderstanding
from app.services.redis_service import redis_service
from app.services.creative_memory import CreativeMemory
import uuid
import logging

logger = logging.getLogger(__name__)


class AssetIntelligence:
    @staticmethod
    async def classify_asset(asset_id: str, asset_type: str = "video", user_id: Optional[str] = None) -> Dict[str, Any]:
        understanding = await MediaUnderstanding.understand_asset(asset_id, asset_type, user_id)
        classification = AssetIntelligence._derive_classification(understanding)
        tags = AssetIntelligence._derive_tags(understanding)
        semantic_description = AssetIntelligence._derive_semantic_description(understanding)

        result = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "classification": classification,
            "tags": tags,
            "semantic_description": semantic_description,
            "understanding": understanding,
        }

        try:
            if redis_service.is_connected():
                await redis_service.set_json(f"asset:intelligence:{asset_id}", result, ex=86400 * 30)
        except Exception:
            pass

        return result

    @staticmethod
    async def batch_classify(asset_ids: List[str], asset_type: str = "video", user_id: Optional[str] = None) -> Dict[str, Any]:
        results = []
        for asset_id in asset_ids:
            classification = await AssetIntelligence.classify_asset(asset_id, asset_type, user_id)
            results.append(classification)
        return {"batch_id": str(uuid.uuid4()), "total": len(results), "results": results}

    @staticmethod
    async def semantic_search(project_id: str, query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        try:
            if redis_service.is_connected():
                pattern = "asset:intelligence:*"
                keys = await redis_service._client.keys(pattern) if redis_service._client else []
                for key in keys:
                    data = await redis_service.get_json(key)
                    if data:
                        if AssetIntelligence._matches_query(data, query):
                            results.append(data)
        except Exception:
            pass

        if not results:
            results = await MediaUnderstanding.semantic_search(project_id, query, user_id)

        return results

    @staticmethod
    def _matches_query(data: Dict[str, Any], query: str) -> bool:
        query_lower = query.lower()
        searchable = f"{data.get('semantic_description', '')} {data.get('classification', {}).get('primary', '')} {' '.join(data.get('tags', []))}"
        return query_lower in searchable.lower()

    @staticmethod
    def _derive_classification(understanding: Dict[str, Any]) -> Dict[str, Any]:
        visual = understanding.get("visual", {})
        objects = visual.get("objects", [])
        faces = visual.get("faces", [])

        categories = {}
        for obj in objects:
            cat = obj.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        if faces:
            categories["face"] = categories.get("face", 0) + len(faces)

        primary = max(categories, key=categories.get) if categories else "unknown"
        secondary = [k for k in categories if k != primary][:3]

        return {
            "primary": primary,
            "secondary": secondary,
            "all_categories": list(categories.keys()),
            "confidence": min(1.0, sum(categories.values()) / 10.0),
        }

    @staticmethod
    def _derive_tags(understanding: Dict[str, Any]) -> List[str]:
        tags = []
        visual = understanding.get("visual", {})
        for obj in visual.get("objects", []):
            label = obj.get("label", "").lower()
            if label:
                tags.append(label)

        metadata = understanding.get("metadata", {})
        tags.extend(metadata.get("tags", []))

        return list(set(tags))[:20]

    @staticmethod
    def _derive_semantic_description(understanding: Dict[str, Any]) -> str:
        visual = understanding.get("visual", {})
        objects = visual.get("objects", [])
        faces = visual.get("faces", [])

        parts = []
        if faces:
            parts.append(f"{len(faces)} person(s) detected")
        if objects:
            labels = [o.get("label", "") for o in objects[:5]]
            parts.append(f"objects: {', '.join(labels)}")

        return ". ".join(parts) if parts else "No significant objects detected"
