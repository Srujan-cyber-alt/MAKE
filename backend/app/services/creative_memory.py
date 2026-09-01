"""
Creative Memory for MAKE AI Video.

Remembers project-level:
- characters
- products
- worlds
- styles
- camera preferences
- color looks
- audio preferences
- previous prompts
- successful generations
- rejected generations
- brand rules

Example:
"Make another ad like the previous one but more energetic."

MAKE should understand "previous one."
"""

from typing import Optional, List, Dict, Any
from app.services.redis_service import redis_service
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class CreativeMemory:
    @staticmethod
    async def remember_project_context(
        project_id: str,
        user_id: str,
        context_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        memory_id = f"memory:{project_id}:{context_type}:{uuid.uuid4()}"
        memory = {
            "memory_id": memory_id,
            "project_id": project_id,
            "user_id": user_id,
            "context_type": context_type,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if redis_service.is_connected():
            await redis_service.set_json(memory_id, memory, ex=86400 * 30)
            await redis_service._client.lpush(f"memory:project:{project_id}", memory_id) if redis_service._client else None
        
        return memory

    @staticmethod
    async def get_project_context(project_id: str, context_type: Optional[str] = None) -> List[Dict[str, Any]]:
        memories = []
        if redis_service.is_connected():
            key = f"memory:project:{project_id}"
            memory_ids = await redis_service._client.lrange(key, 0, 100) if redis_service._client else []
            for memory_id in memory_ids:
                memory = await redis_service.get_json(memory_id)
                if memory:
                    if context_type is None or memory.get("context_type") == context_type:
                        memories.append(memory)
        return memories

    @staticmethod
    async def remember_successful_generation(
        project_id: str,
        user_id: str,
        prompt: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await CreativeMemory.remember_project_context(
            project_id=project_id,
            user_id=user_id,
            context_type="successful_generation",
            data={
                "prompt": prompt,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    async def remember_rejected_generation(
        project_id: str,
        user_id: str,
        prompt: str,
        result: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        return await CreativeMemory.remember_project_context(
            project_id=project_id,
            user_id=user_id,
            context_type="rejected_generation",
            data={
                "prompt": prompt,
                "result": result,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    async def remember_style_preference(project_id: str, user_id: str, style: Dict[str, Any]) -> Dict[str, Any]:
        return await CreativeMemory.remember_project_context(
            project_id=project_id,
            user_id=user_id,
            context_type="style_preference",
            data=style,
        )

    @staticmethod
    async def get_style_preferences(project_id: str) -> List[Dict[str, Any]]:
        memories = await CreativeMemory.get_project_context(project_id, "style_preference")
        return [m.get("data", {}) for m in memories]

    @staticmethod
    async def find_similar_project(user_id: str, objective: str) -> Optional[Dict[str, Any]]:
        if not redis_service.is_connected():
            return None
        
        keys = await redis_service._client.keys(f"memory:project:*") if redis_service._client else []
        for key in keys:
            memory_ids = await redis_service._client.lrange(key, 0, 10) if redis_service._client else []
            for memory_id in memory_ids:
                memory = await redis_service.get_json(memory_id)
                if memory and memory.get("user_id") == user_id:
                    data = memory.get("data", {})
                    prompt = data.get("prompt", "")
                    if prompt and objective.lower() in prompt.lower():
                        return memory
        return None
