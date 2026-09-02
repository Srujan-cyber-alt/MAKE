"""
Routing Audit for MAKE AI Video Phase 16.

Every routing decision is explainable and auditable.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import uuid
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class RoutingAudit:
    def __init__(self, redis_service_instance=None):
        self.redis = redis_service_instance or redis_service
        self._audit_key = "routing:audit"
        self._max_events = 10000

    async def record_routing_decision(self, decision: Dict[str, Any]):
        entry = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "request_requirements": decision.get("request_requirements", {}),
            "candidate_models": decision.get("candidate_models", []),
            "eliminated_candidates": decision.get("eliminated_candidates", []),
            "selected_model": decision.get("selected_model"),
            "fallback_chain": decision.get("fallback_chain", []),
            "routing_mode": decision.get("routing_mode"),
            "score_components": decision.get("score_components", {}),
            "total_score": decision.get("total_score"),
            "user_id": decision.get("user_id"),
            "project_id": decision.get("project_id"),
        }
        try:
            if self.redis.is_connected():
                await self.redis._client.lpush(self._audit_key, str(entry))
                await self.redis._client.ltrim(self._audit_key, 0, self._max_events)
                await self.redis._client.expire(self._audit_key, 86400 * 90)
        except Exception:
            pass
        logger.info(f"Routing audit recorded: {entry['audit_id']} selected={entry['selected_model']}")
        return entry

    async def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            if self.redis.is_connected():
                raw_events = await self.redis._client.lrange(self._audit_key, 0, limit)
                events = []
                for raw in raw_events:
                    try:
                        event = eval(raw) if isinstance(raw, str) else raw
                        events.append(event)
                    except Exception:
                        continue
                return events
        except Exception:
            pass
        return []

    async def get_routing_history(self, model_id: str = None, provider_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        events = await self.get_audit_log(limit=1000)
        filtered = []
        for event in events:
            selected = event.get("selected_model", {})
            if model_id and selected.get("model_id") != model_id:
                continue
            if provider_id and selected.get("provider_id") != provider_id:
                continue
            filtered.append(event)
        return filtered[:limit]

    def explain_routing_decision(self, decision: Dict[str, Any]) -> str:
        selected = decision.get("selected_model")
        if not selected:
            return "No model was selected."

        explanations = []
        reasons = selected.get("reasons", [])
        if reasons:
            explanations.append(f"MAKE selected {selected.get('display_name', selected.get('model_id'))} because it supports:")
            for reason in reasons[:5]:
                explanations.append(f"- {reason}")
        else:
            explanations.append(f"MAKE selected {selected.get('model_id')} as the best available option.")

        fallbacks = decision.get("fallback_chain", [])
        if fallbacks:
            explanations.append("\nFallback options:")
            for fb in fallbacks[:3]:
                explanations.append(f"- {fb.get('model_id')} (score: {fb.get('score', 0):.1f})")

        return "\n".join(explanations)


routing_audit = RoutingAudit()
