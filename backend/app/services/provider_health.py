from datetime import datetime
from typing import Optional, Dict, Any
from app.providers.base import ProviderHealth, VideoProviderAdapter
from app.services.redis_service import redis_service


class ProviderHealthService:
    HEALTH_PREFIX = "provider:health:"
    DEFAULT_TTL = 300

    def __init__(self, redis_service_instance=None):
        self.redis = redis_service_instance or redis_service

    async def get_health(self, provider_name: str) -> Optional[ProviderHealth]:
        if not self.redis.is_available():
            return None

        key = f"{self.HEALTH_PREFIX}{provider_name}"
        data = await self.redis.get(key)
        if not data:
            return None

        try:
            parsed = json.loads(data) if isinstance(data, str) else data
            return ProviderHealth(
                status=parsed.get("status", "unknown"),
                latency_ms=parsed.get("latency_ms"),
                error=parsed.get("error"),
                checked_at=datetime.fromisoformat(parsed.get("checked_at", datetime.utcnow().isoformat())),
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    async def set_health(self, provider_name: str, health: ProviderHealth, ttl: int = None) -> bool:
        if not self.redis.is_available():
            return False

        key = f"{self.HEALTH_PREFIX}{provider_name}"
        data = {
            "status": health.status,
            "latency_ms": health.latency_ms,
            "error": health.error,
            "checked_at": health.checked_at.isoformat() if health.checked_at else datetime.utcnow().isoformat(),
        }
        return await self.redis.set(key, json.dumps(data), ex=ttl or self.DEFAULT_TTL)

    async def check_and_cache(self, provider: VideoProviderAdapter) -> ProviderHealth:
        try:
            health = await provider.health_check()
        except Exception as e:
            health = ProviderHealth(status="error", error=str(e))

        await self.set_health(provider.name, health)
        return health

    async def get_all_health(self, providers: Dict[str, VideoProviderAdapter]) -> Dict[str, ProviderHealth]:
        results = {}
        for name, provider in providers.items():
            health = await self.get_health(name)
            if not health:
                health = await self.check_and_cache(provider)
            results[name] = health
        return results


import json

provider_health_service = ProviderHealthService()
