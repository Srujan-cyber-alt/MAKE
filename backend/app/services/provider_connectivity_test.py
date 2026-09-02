"""
Provider Connectivity Test for MAKE AI Video Phase 16.

Health checks without triggering paid generation.
"""

from typing import Optional, Dict, List, Any
import logging
from app.services.canonical_provider_registry import CanonicalProviderRegistry

logger = logging.getLogger(__name__)


class ProviderConnectivityTest:
    def __init__(self, provider_registry: CanonicalProviderRegistry):
        self.provider_registry = provider_registry

    async def test_all_providers(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for provider_id, data in self.provider_registry.get_all_providers().items():
            result = await self.test_provider(provider_id)
            results[provider_id] = result
        return results

    async def test_provider(self, provider_id: str) -> Dict[str, Any]:
        data = self.provider_registry.get_provider(provider_id)
        if not data:
            return {"provider_id": provider_id, "status": "unknown", "error": "Provider not found"}

        adapter = data.get("adapter")
        if not adapter:
            return {"provider_id": provider_id, "status": "not_configured", "error": "No adapter configured"}

        try:
            health = await adapter.health_check()
            status = health.status.value if hasattr(health.status, 'value') else health.status
            return {
                "provider_id": provider_id,
                "status": status,
                "latency_ms": health.latency_ms,
                "error": health.error,
                "reachable": status == "available",
                "credentials_valid": status != "auth_error",
            }
        except Exception as e:
            return {
                "provider_id": provider_id,
                "status": "unreachable",
                "error": str(e),
                "reachable": False,
                "credentials_valid": False,
            }

    async def test_model_availability(self, provider_id: str, model_id: str) -> Dict[str, Any]:
        data = self.provider_registry.get_provider(provider_id)
        if not data:
            return {"available": False, "error": "Provider not found"}
        adapter = data.get("adapter")
        if not adapter:
            return {"available": False, "error": "No adapter"}
        models = adapter.get_supported_models()
        available = any(m.id == model_id for m in models)
        return {"available": available, "model_id": model_id}


provider_connectivity_test = ProviderConnectivityTest
