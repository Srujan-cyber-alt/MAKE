"""
World / Location Consistency System for MAKE AI Video.

Allows reusable environments.

A location profile contains:
- architecture
- geography
- lighting
- weather
- time
- colors
- materials
- props
- atmosphere
- spatial relationships
"""

from typing import Optional, List, Dict, Any
from app.services.redis_service import redis_service
import uuid
import logging

logger = logging.getLogger(__name__)


class WorldSystem:
    @staticmethod
    async def create_world(
        name: str,
        user_id: str,
        architecture: Optional[str] = None,
        geography: Optional[str] = None,
        lighting: Optional[str] = None,
        weather: Optional[str] = None,
        time: Optional[str] = None,
        colors: Optional[Dict[str, Any]] = None,
        materials: Optional[List[str]] = None,
        props: Optional[List[str]] = None,
        atmosphere: Optional[str] = None,
        spatial_relationships: Optional[Dict[str, Any]] = None,
        reference_images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        world_id = f"world:{uuid.uuid4()}"
        world_data = {
            "world_id": world_id,
            "name": name,
            "user_id": user_id,
            "architecture": architecture or "",
            "geography": geography or "",
            "lighting": lighting or "cinematic",
            "weather": weather or "clear",
            "time": time or "golden hour",
            "colors": colors or {},
            "materials": materials or [],
            "props": props or [],
            "atmosphere": atmosphere or "neutral",
            "spatial_relationships": spatial_relationships or {},
            "reference_images": reference_images or [],
            "constraints": [
                "lighting must remain consistent",
                "architecture must match",
                "atmosphere must be preserved",
            ],
        }
        
        if redis_service.is_connected():
            await redis_service.set_json(world_id, world_data, ex=86400 * 30)
        
        logger.info(f"Created world {world_id}: {name}")
        return world_data

    @staticmethod
    async def get_world(world_id: str) -> Optional[Dict[str, Any]]:
        try:
            if redis_service.is_connected():
                data = await redis_service.get_json(world_id)
                if data:
                    return data
        except Exception:
            pass
        return None

    @staticmethod
    async def list_worlds(user_id: str) -> List[Dict[str, Any]]:
        worlds = []
        try:
            if redis_service.is_connected():
                pattern = "world:*"
                keys = await redis_service._client.keys(pattern) if redis_service._client else []
                for key in keys:
                    data = await redis_service.get_json(key)
                    if data and data.get("user_id") == user_id:
                        worlds.append(data)
        except Exception:
            pass
        return worlds

    @staticmethod
    async def update_world(world_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        world = await WorldSystem.get_world(world_id)
        if not world:
            return None
        
        world.update(updates)
        world["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        
        if redis_service.is_connected():
            await redis_service.set_json(world_id, world, ex=86400 * 30)
        
        return world

    @staticmethod
    async def delete_world(world_id: str) -> bool:
        if redis_service.is_connected():
            await redis_service._client.delete(world_id) if redis_service._client else None
        return True

    @staticmethod
    def validate_world_consistency(world: Dict[str, Any], new_scene: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        if world.get("lighting") and new_scene.get("lighting"):
            if world["lighting"] != new_scene["lighting"]:
                issues.append(f"Lighting mismatch: world has '{world['lighting']}', scene has '{new_scene['lighting']}'")
        
        if world.get("time") and new_scene.get("time"):
            if world["time"] != new_scene["time"]:
                issues.append(f"Time mismatch: world has '{world['time']}', scene has '{new_scene['time']}'")
        
        if world.get("weather") and new_scene.get("weather"):
            if world["weather"] != new_scene["weather"]:
                issues.append(f"Weather mismatch: world has '{world['weather']}', scene has '{new_scene['weather']}'")
        
        return {
            "consistent": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    async def create_world_lock(world_id: str) -> Dict[str, Any]:
        world = await WorldSystem.get_world(world_id)
        if not world:
            return {"error": "World not found"}
        
        lock = {
            "world_id": world_id,
            "locked": True,
            "locked_at": __import__("datetime").datetime.utcnow().isoformat(),
            "locked_attributes": {
                "lighting": world.get("lighting"),
                "time": world.get("time"),
                "weather": world.get("weather"),
                "atmosphere": world.get("atmosphere"),
                "architecture": world.get("architecture"),
            },
        }
        
        if redis_service.is_connected():
            await redis_service.set_json(f"world_lock:{world_id}", lock, ex=86400 * 30)
        
        return lock

    @staticmethod
    async def validate_world_lock(world_id: str, new_scene: Dict[str, Any]) -> Dict[str, Any]:
        lock = None
        try:
            if redis_service.is_connected():
                lock = await redis_service.get_json(f"world_lock:{world_id}")
        except Exception:
            pass
        
        if not lock or not lock.get("locked"):
            return {"locked": False, "consistent": True}
        
        issues = []
        locked_attrs = lock.get("locked_attributes", {})
        
        for attr, value in locked_attrs.items():
            if value and new_scene.get(attr) and new_scene[attr] != value:
                issues.append(f"World lock violation: {attr} changed from '{value}' to '{new_scene[attr]}'")
        
        return {
            "locked": True,
            "consistent": len(issues) == 0,
            "issues": issues,
        }
