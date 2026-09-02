"""
Canonical Provider Registry for MAKE AI Video Phase 16.

Tracks provider state, health, authentication, limits, and metadata.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
from app.providers.base import VideoProviderAdapter, ProviderRegistry as LegacyProviderRegistry, ProviderHealth
from app.services.provider_health import provider_health_service

logger = logging.getLogger(__name__)


class CanonicalProviderRegistry:
    _instance = None

    def __init__(self, legacy_registry: LegacyProviderRegistry):
        self.legacy_registry = legacy_registry
        self._providers: Dict[str, Dict[str, Any]] = {}
        self._initialize_from_legacy()

    @classmethod
    def get_instance(cls, legacy_registry: LegacyProviderRegistry = None) -> "CanonicalProviderRegistry":
        if cls._instance is None and legacy_registry:
            cls._instance = cls(legacy_registry)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _initialize_from_legacy(self):
        for name, provider in self.legacy_registry.get_all().items():
            self._providers[name] = {
                "id": name,
                "name": name,
                "provider_type": provider.__class__.__name__,
                "environment_requirements": {},
                "authentication_status": "unknown",
                "api_status": "unknown",
                "supported_models": [m.id for m in provider.get_supported_models()],
                "rate_limits": {},
                "concurrency_limits": {},
                "region": None,
                "health": {},
                "latency": None,
                "error_rate": 0.0,
                "cost_information": {},
                "metadata": {},
                "adapter": provider,
            }

    def register_provider(self, provider: VideoProviderAdapter, provider_type: str = "unknown"):
        self._providers[provider.name] = {
            "id": provider.name,
            "name": provider.name,
            "provider_type": provider_type,
            "environment_requirements": {},
            "authentication_status": "unknown",
            "api_status": "unknown",
            "supported_models": [m.id for m in provider.get_supported_models()],
            "rate_limits": {},
            "concurrency_limits": {},
            "region": None,
            "health": {},
            "latency": None,
            "error_rate": 0.0,
            "cost_information": {},
            "metadata": {},
            "adapter": provider,
        }

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return self._providers.get(provider_id)

    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._providers)

    def get_available_providers(self) -> List[str]:
        available = []
        for name, data in self._providers.items():
            if data.get("api_status") in ("available",):
                available.append(name)
        return available

    def get_provider_status(self, provider_id: str) -> Optional[str]:
        provider = self._providers.get(provider_id)
        return provider.get("api_status") if provider else None

    def update_provider_status(self, provider_id: str, status: str, error: str = None):
        if provider_id in self._providers:
            self._providers[provider_id]["api_status"] = status
            if error:
                self._providers[provider_id]["last_error"] = error

    def update_provider_health(self, provider_id: str, health: ProviderHealth):
        if provider_id in self._providers:
            self._providers[provider_id]["health"] = {
                "status": health.status.value if hasattr(health.status, 'value') else health.status,
                "latency_ms": health.latency_ms,
                "error": health.error,
                "checked_at": health.checked_at.isoformat() if health.checked_at else None,
                "success_rate": health.success_rate,
                "failure_rate": health.failure_rate,
                "timeout_rate": health.timeout_rate,
                "validation_failure_rate": health.validation_failure_rate,
                "rate_limit_frequency": health.rate_limit_frequency,
                "recent_incidents": health.recent_incidents,
            }
            self._providers[provider_id]["latency"] = health.latency_ms
            self._providers[provider_id]["error_rate"] = health.failure_rate

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        results = {}
        for provider_id, data in self._providers.items():
            try:
                adapter = data.get("adapter")
                if adapter:
                    health = await adapter.health_check()
                    self.update_provider_health(provider_id, health)
                    results[provider_id] = health
                    if health.status.value == "available":
                        self.update_provider_status(provider_id, "available")
                    elif health.status.value == "degraded":
                        self.update_provider_status(provider_id, "degraded")
                    else:
                        self.update_provider_status(provider_id, health.status.value)
                else:
                    self.update_provider_status(provider_id, "not_configured")
            except Exception as e:
                self.update_provider_status(provider_id, "unavailable", str(e))
                results[provider_id] = ProviderHealth(
                    status="unavailable",
                    error=str(e),
                )
        return results

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for provider_id, data in self._providers.items():
            result[provider_id] = {
                "id": data["id"],
                "name": data["name"],
                "provider_type": data["provider_type"],
                "authentication_status": data["authentication_status"],
                "api_status": data["api_status"],
                "supported_models": data["supported_models"],
                "rate_limits": data["rate_limits"],
                "concurrency_limits": data["concurrency_limits"],
                "region": data["region"],
                "health": data["health"],
                "latency": data["latency"],
                "error_rate": data["error_rate"],
                "cost_information": data["cost_information"],
            }
        return result
