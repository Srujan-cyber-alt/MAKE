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
    ) -> CharacterDefinition:
        character_id = str(uuid.uuid4())
        identity_profile = await IdentityLockV2.create_profile(
            entity_type="character",
            name=name,
            reference_asset_ids=reference_images or [],
            mode="balanced",
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
            },
        )
        profile_id = identity_profile.profile_id

        character = CharacterDefinition(
            character_id=character_id,
            name=name,
            age_range=age_range,
            appearance=appearance or {},
            hair=hair or {},
            face=face or {},
            body=body or {},
            clothing=clothing or {},
            accessories=accessories or [],
            personality=personality,
            voice=voice,
            movement=movement or {},
            reference_images=reference_images or [],
            identity_profile_id=profile_id,
        )

        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character.model_dump(), ex=86400)

        logger.info(f"Created character {character_id}: {name}")
        return character

    @staticmethod
    async def get_character(character_id: str) -> Optional[Dict[str, Any]]:
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            return await redis_service.get_json(f"character:{character_id}")
        return None

    @staticmethod
    async def update_character(character_id: str, updates: Dict[str, Any]) -> Optional[CharacterDefinition]:
        character_data = await CharacterSystem.get_character(character_id)
        if not character_data:
            return None
        character_data.update(updates)
        character = CharacterDefinition(**character_data)
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"character:{character_id}", character.model_dump(), ex=86400)
        return character


def redis_service_is_connected():
    try:
        from app.services.redis_service import redis_service
        return redis_service.is_connected()
    except Exception:
        return False
