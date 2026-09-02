"""
Cost Engine for MAKE AI Video Phase 16.

Tracks generation costs without inventing prices.
Unknown costs remain UNKNOWN.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class CostEngine:
    def __init__(self, redis_service_instance=None):
        self.redis = redis_service_instance or redis_service
        self._cost_key = "cost:tracking"
        self._project_cost_key = "cost:project"

    async def record_cost(self, generation_id: str, model_id: str, provider_id: str, cost: Optional[float], metadata: Dict[str, Any] = None):
        entry = {
            "generation_id": generation_id,
            "model_id": model_id,
            "provider_id": provider_id,
            "cost": cost,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        try:
            if self.redis.is_connected():
                await self.redis._client.lpush(self._cost_key, str(entry))
                await self.redis._client.ltrim(self._cost_key, 0, 50000)
                await self.redis._client.expire(self._cost_key, 86400 * 90)
        except Exception:
            pass

    async def estimate_cost(self, model_id: str, provider_id: str, duration_seconds: float, resolution: tuple = None) -> Optional[float]:
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        if not registry:
            return None
        model = registry.get_model(model_id)
        if not model or model.limits.cost_per_second is None:
            return None
        base_cost = model.limits.cost_per_second * duration_seconds
        if resolution and model.cost_profile.get("resolution_multipliers"):
            w, h = resolution
            key = f"{w}x{h}"
            multiplier = model.cost_profile["resolution_multipliers"].get(key, 1.0)
            base_cost *= multiplier
        return base_cost

    async def get_project_cost(self, project_id: str) -> Dict[str, Any]:
        try:
            if self.redis.is_connected():
                raw = await self.redis.get(f"{self._project_cost_key}:{project_id}")
                if raw:
                    return raw if isinstance(raw, dict) else {}
        except Exception:
            pass
        return {"project_id": project_id, "total_cost": 0.0, "generations": 0}

    async def accumulate_project_cost(self, project_id: str, cost: float):
        try:
            if self.redis.is_connected():
                key = f"{self._project_cost_key}:{project_id}"
                current = await self.get_project_cost(project_id)
                current["total_cost"] = current.get("total_cost", 0.0) + cost
                current["generations"] = current.get("generations", 0) + 1
                await self.redis.set(key, current, ex=86400 * 90)
        except Exception:
            pass

    async def get_model_cost_stats(self, model_id: str, provider_id: str) -> Dict[str, Any]:
        try:
            if self.redis.is_connected():
                raw_events = await self.redis._client.lrange(self._cost_key, 0, 5000)
                events = []
                for raw in raw_events:
                    try:
                        event = eval(raw) if isinstance(raw, str) else raw
                        if event.get("model_id") == model_id and event.get("provider_id") == provider_id:
                            events.append(event)
                    except Exception:
                        continue
                if events:
                    costs = [e["cost"] for e in events if e.get("cost") is not None]
                    return {
                        "model_id": model_id,
                        "provider_id": provider_id,
                        "total_generations": len(events),
                        "total_cost": sum(costs) if costs else 0.0,
                        "avg_cost": sum(costs) / len(costs) if costs else 0.0,
                        "unknown_cost_count": sum(1 for e in events if e.get("cost") is None),
                    }
        except Exception:
            pass
        return {"model_id": model_id, "provider_id": provider_id, "total_cost": 0.0}


cost_engine = CostEngine()
