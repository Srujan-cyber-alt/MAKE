"""
Provider Health Engine for MAKE AI Video Phase 16.

Upgraded health tracking with rolling windows, metrics, and automatic degradation.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from collections import deque
import logging
from app.providers.base import VideoProviderAdapter, ProviderHealth as LegacyProviderHealth
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class ProviderHealthEngine:
    def __init__(self, redis_service_instance=None):
        self.redis = redis_service_instance or redis_service
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._rolling_window_seconds = 3600
        self._max_events = 1000

    def record_event(self, provider_id: str, event_type: str, metadata: Dict[str, Any] = None):
        if provider_id not in self._metrics:
            self._metrics[provider_id] = {
                "events": deque(maxlen=self._max_events),
                "success_count": 0,
                "failure_count": 0,
                "timeout_count": 0,
                "validation_failure_count": 0,
                "rate_limit_count": 0,
                "recent_incidents": [],
            }

        provider_metrics = self._metrics[provider_id]
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        provider_metrics["events"].append(event)

        if event_type == "success":
            provider_metrics["success_count"] += 1
        elif event_type == "failure":
            provider_metrics["failure_count"] += 1
        elif event_type == "timeout":
            provider_metrics["timeout_count"] += 1
        elif event_type == "validation_failure":
            provider_metrics["validation_failure_count"] += 1
        elif event_type == "rate_limit":
            provider_metrics["rate_limit_count"] += 1
            provider_metrics["recent_incidents"].append({
                "type": "rate_limit",
                "timestamp": datetime.utcnow().isoformat(),
            })

        cutoff = datetime.utcnow() - timedelta(seconds=self._rolling_window_seconds)
        recent = [e for e in provider_metrics["events"] if datetime.fromisoformat(e["timestamp"]) > cutoff]
        provider_metrics["events"] = deque(recent, maxlen=self._max_events)

        if self.redis.is_connected():
            try:
                key = f"provider:health:engine:{provider_id}"
                self.redis._client.lpush(key, f"{event_type}:{datetime.utcnow().isoformat()}")
                self.redis._client.ltrim(key, 0, self._max_events - 1)
                self.redis._client.expire(key, self._rolling_window_seconds)
            except Exception:
                pass

    def get_health(self, provider_id: str) -> LegacyProviderHealth:
        metrics = self._metrics.get(provider_id, {
            "success_count": 0,
            "failure_count": 0,
            "timeout_count": 0,
            "validation_failure_count": 0,
            "rate_limit_count": 0,
            "recent_incidents": [],
        })

        total = metrics["success_count"] + metrics["failure_count"]
        if total == 0:
            status = "unknown"
            success_rate = 1.0
            failure_rate = 0.0
        else:
            success_rate = metrics["success_count"] / total
            failure_rate = metrics["failure_count"] / total

        if success_rate > 0.9 and metrics["rate_limit_count"] < 3:
            status = "available"
        elif success_rate > 0.7:
            status = "degraded"
        elif total > 0:
            status = "unavailable"
        else:
            status = "unknown"

        return LegacyProviderHealth(
            status=status,
            latency_ms=metrics.get("last_latency_ms"),
            error=metrics.get("last_error"),
        )

    def get_all_health(self) -> Dict[str, LegacyProviderHealth]:
        results = {}
        for provider_id in self._metrics.keys():
            results[provider_id] = self.get_health(provider_id)
        return results

    def record_success(self, provider_id: str, latency_ms: float = None, metadata: Dict[str, Any] = None):
        self.record_event(provider_id, "success", {**(metadata or {}), "latency_ms": latency_ms})

    def record_failure(self, provider_id: str, error: str = None, metadata: Dict[str, Any] = None):
        self.record_event(provider_id, "failure", {**(metadata or {}), "error": error})

    def record_timeout(self, provider_id: str, metadata: Dict[str, Any] = None):
        self.record_event(provider_id, "timeout", metadata or {})

    def record_validation_failure(self, provider_id: str, metadata: Dict[str, Any] = None):
        self.record_event(provider_id, "validation_failure", metadata or {})

    def record_rate_limit(self, provider_id: str, metadata: Dict[str, Any] = None):
        self.record_event(provider_id, "rate_limit", metadata or {})

    def get_provider_score(self, provider_id: str) -> float:
        health = self.get_health(provider_id)
        if health.status == "available":
            return 1.0
        elif health.status == "degraded":
            return 0.5
        elif health.status == "unknown":
            return 0.3
        return 0.0

    def should_degrade(self, provider_id: str) -> bool:
        health = self.get_health(provider_id)
        return health.status in ("degraded", "unavailable")

    def get_metrics_summary(self, provider_id: str) -> Dict[str, Any]:
        metrics = self._metrics.get(provider_id, {})
        return {
            "success_count": metrics.get("success_count", 0),
            "failure_count": metrics.get("failure_count", 0),
            "timeout_count": metrics.get("timeout_count", 0),
            "validation_failure_count": metrics.get("validation_failure_count", 0),
            "rate_limit_count": metrics.get("rate_limit_count", 0),
            "recent_incidents": metrics.get("recent_incidents", []),
        }


provider_health_engine = ProviderHealthEngine()
