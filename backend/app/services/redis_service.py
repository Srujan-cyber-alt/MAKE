import json
import os
from typing import Optional, Any
from app.core.config import settings

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisService:
    def __init__(self):
        self._client = None
        self._enabled = False
        if REDIS_AVAILABLE and settings.redis_url:
            try:
                self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
                self._enabled = True
            except Exception:
                self._enabled = False

    async def get(self, key: str) -> Optional[str]:
        if not self._enabled:
            return None
        try:
            return await self._client.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if not self._enabled:
            return False
        try:
            await self._client.set(key, value, ex=ex)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        if not self._enabled:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.close()


redis_service = RedisService()
