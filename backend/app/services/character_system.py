from typing import Optional, List, Dict, Any
from app.schemas.phase9 import CharacterDefinition
from app.services.identity_lock_v2 import IdentityLockV2
import uuid
import logging

logger = logging.getLogger(__name__)


class CharacterSystem:
    @staticmethod
    async def create_character(
        name: str,
        age_range: Optional[str] = None,
        appearance: Optional[Dict[str, Any]] = None,
        hair: Optional[Dict[str, Any]] = None,
        face: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        clothing: Optional[Dict[str, Any]] = None,
        accessories: Optional[List[str]] = None,
        personality: Optional[str] = None,
        voice: Optional[str] = None,
        movement: Optional[Dict[str, Any]] = None,
        reference_images: Optional[List[str]] = None,
        negative_constraints: Optional[List[str]] = None,
        identity_embedding: Optional[str] = None,
    ) -> Dict[str, Any]:
        character_id = str(uuid.uuid4())
        identity_profile = await IdentityLockV2.create_profile(
            entity_type="character",
            name=name,
            reference_asset_ids=reference_images or [],
            mode="strict",
            attributes={
                "age_range": age_range,
                "appearance": appearance or {},
                "hair": hair or {},
                "face": face or {},
                "body": body or {},
                "clothing": clothing or {},
                "accessories": accessories or [],
                "personality": personality,
                "voice": voice,
                "movement": movement or {},
                "skin_appearance": appearance.get("skin", "smooth") if appearance else "smooth",
            },
        )
        profile_id = identity_profile.profile_id

        character_data = {
            "character_id": character_id,
            "name": name,
            "age_range": age_range,
            "appearance": appearance or {},
            "hair": hair or {},
            "face": face or {},
            "body": body or {},
            "clothing": clothing or {},
            "accessories": accessories or [],
            "personality": personality,
            "voice": voice,
            "movement": movement or {},
            "reference_images": reference_images or [],
            "identity_profile_id": profile_id,
            "negative_constraints": negative_constraints or [
                "do not change face identity",
                "do not change body proportions",
                "do not change hairstyle",
                "do not change skin tone",
            ],
            "identity_embedding": identity_embedding,
            "wardrobe_history": [],
            "expression_history": [],
            "pose_history": [],
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }

        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character_data, ex=86400 * 30)

        logger.info(f"Created character {character_id}: {name}")
        return character_data

    @staticmethod
    async def get_character(character_id: str) -> Optional[Dict[str, Any]]:
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            return await redis_service.get_json(f"character:{character_id}")
        return None

    @staticmethod
    async def update_character(character_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        character_data = await CharacterSystem.get_character(character_id)
        if not character_data:
            return None
        character_data.update(updates)
        character_data["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character_data, ex=86400 * 30)
        return character_data

    @staticmethod
    async def change_wardrobe(character_id: str, new_clothing: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        character = await CharacterSystem.get_character(character_id)
        if not character:
            return None
        character["wardrobe_history"].append({
            "previous_clothing": character.get("clothing"),
            "new_clothing": new_clothing,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })
        character["clothing"] = new_clothing
        character["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character, ex=86400 * 30)
        return character

    @staticmethod
    async def add_expression(character_id: str, expression: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        character = await CharacterSystem.get_character(character_id)
        if not character:
            return None
        character["expression_history"].append({
            "expression": expression,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character, ex=86400 * 30)
        return character

    @staticmethod
    async def add_pose(character_id: str, pose: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        character = await CharacterSystem.get_character(character_id)
        if not character:
            return None
        character["pose_history"].append({
            "pose": pose,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character, ex=86400 * 30)
        return character
