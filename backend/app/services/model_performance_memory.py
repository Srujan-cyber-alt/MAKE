"""
Model Performance Memory for MAKE AI Video Phase 16.

Learns from generation history to improve routing decisions.
Transparent statistical scoring without opaque ML.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class ModelPerformanceMemory:
    def __init__(self, redis_service_instance=None):
        self.redis = redis_service_instance or redis_service
        self._memory_key = "model:performance:memory"
        self._max_memory_days = 90

    async def record_generation(self, model_id: str, provider_id: str, result: Dict[str, Any]):
        event = {
            "model_id": model_id,
            "provider_id": provider_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": result.get("success", False),
            "quality_score": result.get("quality_score", 0.0),
            "generation_time_seconds": result.get("generation_time_seconds", 0.0),
            "cost": result.get("cost", 0.0),
            "repair_count": result.get("repair_count", 0),
            "validation_passed": result.get("validation_passed", False),
            "user_accepted": result.get("user_accepted", False),
            "request_class": result.get("request_class", "general"),
            "modality": result.get("modality", "video"),
            "resolution": result.get("resolution"),
            "duration_seconds": result.get("duration_seconds"),
            "task_type": result.get("task_type", "unknown"),
            "failure_type": result.get("failure_type"),
        }

        try:
            if self.redis.is_connected():
                await self.redis._client.lpush(self._memory_key, str(event))
                await self.redis._client.ltrim(self._memory_key, 0, 10000)
                await self.redis._client.expire(self._memory_key, 86400 * self._max_memory_days)
        except Exception:
            pass

        logger.info(f"Recorded performance memory: {provider_id}:{model_id} success={event['success']}")

    async def get_model_stats(self, model_id: str, provider_id: str) -> Dict[str, Any]:
        events = await self._get_events(model_id, provider_id)
        if not events:
            return {
                "model_id": model_id,
                "provider_id": provider_id,
                "total_generations": 0,
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "avg_generation_time": 0.0,
                "avg_cost": 0.0,
                "avg_repair_count": 0.0,
                "validation_pass_rate": 0.0,
                "user_acceptance_rate": 0.0,
            }

        total = len(events)
        successes = [e for e in events if e.get("success")]
        validated = [e for e in events if e.get("validation_passed")]
        accepted = [e for e in events if e.get("user_accepted")]

        return {
            "model_id": model_id,
            "provider_id": provider_id,
            "total_generations": total,
            "success_rate": len(successes) / total,
            "avg_quality": sum(e.get("quality_score", 0) for e in events) / total,
            "avg_generation_time": sum(e.get("generation_time_seconds", 0) for e in events) / total,
            "avg_cost": sum(e.get("cost", 0) for e in events) / total,
            "avg_repair_count": sum(e.get("repair_count", 0) for e in events) / total,
            "validation_pass_rate": len(validated) / total,
            "user_acceptance_rate": len(accepted) / total,
        }

    async def get_provider_stats(self, provider_id: str) -> Dict[str, Any]:
        events = await self._get_events_by_provider(provider_id)
        if not events:
            return {"provider_id": provider_id, "total_generations": 0}

        total = len(events)
        return {
            "provider_id": provider_id,
            "total_generations": total,
            "success_rate": sum(1 for e in events if e.get("success")) / total,
            "avg_generation_time": sum(e.get("generation_time_seconds", 0) for e in events) / total,
            "avg_cost": sum(e.get("cost", 0) for e in events) / total,
        }

    async def get_best_models_for_task(self, task_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        events = await self._get_recent_events(days=30)
        task_events = [e for e in events if e.get("task_type") == task_type]

        model_stats = defaultdict(lambda: {
            "model_id": "",
            "provider_id": "",
            "total": 0,
            "success": 0,
            "quality_sum": 0.0,
            "time_sum": 0.0,
            "cost_sum": 0.0,
            "repair_sum": 0,
        })

        for event in task_events:
            key = f"{event.get('provider_id')}:{event.get('model_id')}"
            stats = model_stats[key]
            stats["model_id"] = event.get("model_id")
            stats["provider_id"] = event.get("provider_id")
            stats["total"] += 1
            if event.get("success"):
                stats["success"] += 1
            stats["quality_sum"] += event.get("quality_score", 0)
            stats["time_sum"] += event.get("generation_time_seconds", 0)
            stats["cost_sum"] += event.get("cost", 0)
            stats["repair_sum"] += event.get("repair_count", 0)

        scored = []
        for key, stats in model_stats.items():
            if stats["total"] > 0:
                scored.append({
                    "model_id": stats["model_id"],
                    "provider_id": stats["provider_id"],
                    "score": (stats["success"] / stats["total"]) * 0.4 + (stats["quality_sum"] / stats["total"]) * 0.4 - (stats["cost_sum"] / stats["total"]) * 0.2,
                    "success_rate": stats["success"] / stats["total"],
                    "avg_quality": stats["quality_sum"] / stats["total"],
                    "avg_cost": stats["cost_sum"] / stats["total"],
                    "avg_repair": stats["repair_sum"] / stats["total"],
                    "total_generations": stats["total"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    async def _get_events(self, model_id: str, provider_id: str) -> List[Dict[str, Any]]:
        try:
            if self.redis.is_connected():
                raw_events = await self.redis._client.lrange(self._memory_key, 0, 5000)
                events = []
                for raw in raw_events:
                    try:
                        event = eval(raw) if isinstance(raw, str) else raw
                        if event.get("model_id") == model_id and event.get("provider_id") == provider_id:
                            events.append(event)
                    except Exception:
                        continue
                return events
        except Exception:
            pass
        return []

    async def _get_events_by_provider(self, provider_id: str) -> List[Dict[str, Any]]:
        try:
            if self.redis.is_connected():
                raw_events = await self.redis._client.lrange(self._memory_key, 0, 5000)
                events = []
                for raw in raw_events:
                    try:
                        event = eval(raw) if isinstance(raw, str) else raw
                        if event.get("provider_id") == provider_id:
                            events.append(event)
                    except Exception:
                        continue
                return events
        except Exception:
            pass
        return []

    async def _get_recent_events(self, days: int = 30) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        try:
            if self.redis.is_connected():
                raw_events = await self.redis._client.lrange(self._memory_key, 0, 5000)
                events = []
                for raw in raw_events:
                    try:
                        event = eval(raw) if isinstance(raw, str) else raw
                        ts = datetime.fromisoformat(event.get("timestamp", ""))
                        if ts > cutoff:
                            events.append(event)
                    except Exception:
                        continue
                return events
        except Exception:
            pass
        return []


model_performance_memory = ModelPerformanceMemory()
