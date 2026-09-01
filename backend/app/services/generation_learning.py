"""
Generation Learning Loop for MAKE AI Video.

Tracks:
- prompt
- model
- provider
- settings
- output quality
- repair count
- failure type
- user iteration
- user acceptance
- generation time
- cost

Uses this to improve future routing and prompting.

Does not train models automatically.
Builds the data/feedback architecture for intelligent routing.
"""

from typing import Optional, List, Dict, Any
from app.services.redis_service import redis_service
from app.services.smart_model_router import SmartModelRouter
from app.services.quality_control import QualityControl
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class GenerationLearning:
    @staticmethod
    async def record_generation_event(
        prompt: str,
        model: str,
        provider: str,
        settings: Dict[str, Any],
        output_quality: float,
        repair_count: int = 0,
        failure_type: Optional[str] = None,
        user_iteration: int = 1,
        user_accepted: bool = False,
        generation_time_seconds: float = 0.0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        event_id = f"learning:{uuid.uuid4()}"
        event = {
            "event_id": event_id,
            "prompt": prompt,
            "model": model,
            "provider": provider,
            "settings": settings,
            "output_quality": output_quality,
            "repair_count": repair_count,
            "failure_type": failure_type,
            "user_iteration": user_iteration,
            "user_accepted": user_accepted,
            "generation_time_seconds": generation_time_seconds,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if redis_service.is_connected():
            await redis_service.set_json(event_id, event, ex=86400 * 90)
            await redis_service._client.lpush("learning:events", event_id) if redis_service._client else None
        
        logger.info(f"Recorded learning event {event_id}: model={model}, quality={output_quality}, accepted={user_accepted}")
        return event

    @staticmethod
    async def get_model_performance(model: str, provider: str) -> Dict[str, Any]:
        events = []
        if redis_service.is_connected():
            event_ids = await redis_service._client.lrange("learning:events", 0, 1000) if redis_service._client else []
            for event_id in event_ids:
                event = await redis_service.get_json(event_id)
                if event and event.get("model") == model and event.get("provider") == provider:
                    events.append(event)
        
        if not events:
            return {"model": model, "provider": provider, "total_generations": 0}
        
        total = len(events)
        avg_quality = sum(e.get("output_quality", 0) for e in events) / total
        avg_time = sum(e.get("generation_time_seconds", 0) for e in events) / total
        avg_cost = sum(e.get("cost", 0) for e in events) / total
        acceptance_rate = sum(1 for e in events if e.get("user_accepted")) / total
        failure_rate = sum(1 for e in events if e.get("failure_type")) / total
        avg_repairs = sum(e.get("repair_count", 0) for e in events) / total
        
        return {
            "model": model,
            "provider": provider,
            "total_generations": total,
            "avg_quality": avg_quality,
            "avg_time": avg_time,
            "avg_cost": avg_cost,
            "acceptance_rate": acceptance_rate,
            "failure_rate": failure_rate,
            "avg_repairs": avg_repairs,
            "success_rate": 1.0 - failure_rate,
        }

    @staticmethod
    async def get_best_models_for_capability(capability: str, limit: int = 5) -> List[Dict[str, Any]]:
        events = []
        if redis_service.is_connected():
            event_ids = await redis_service._client.lrange("learning:events", 0, 5000) if redis_service._client else []
            for event_id in event_ids:
                event = await redis_service.get_json(event_id)
                if event:
                    events.append(event)
        
        model_stats = {}
        for event in events:
            key = f"{event.get('provider')}:{event.get('model')}"
            if key not in model_stats:
                model_stats[key] = {
                    "model": event.get("model"),
                    "provider": event.get("provider"),
                    "total": 0,
                    "accepted": 0,
                    "quality_sum": 0.0,
                    "cost_sum": 0.0,
                    "repair_sum": 0,
                }
            stats = model_stats[key]
            stats["total"] += 1
            if event.get("user_accepted"):
                stats["accepted"] += 1
            stats["quality_sum"] += event.get("output_quality", 0)
            stats["cost_sum"] += event.get("cost", 0)
            stats["repair_sum"] += event.get("repair_count", 0)
        
        scored = []
        for key, stats in model_stats.items():
            if stats["total"] > 0:
                scored.append({
                    "model": stats["model"],
                    "provider": stats["provider"],
                    "score": (stats["accepted"] / stats["total"]) * 0.5 + (stats["quality_sum"] / stats["total"]) * 0.3 - (stats["cost_sum"] / stats["total"]) * 0.2,
                    "acceptance_rate": stats["accepted"] / stats["total"],
                    "avg_quality": stats["quality_sum"] / stats["total"],
                    "avg_cost": stats["cost_sum"] / stats["total"],
                    "total_generations": stats["total"],
                })
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
