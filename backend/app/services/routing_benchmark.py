"""
Routing Benchmark for MAKE AI Video Phase 20.

Simulates and compares routing decisions using existing ModelRouter4.
"""

from typing import Optional, List, Dict, Any
from app.services.model_router_4 import model_router_4, RoutingMode
from app.services.routing_audit import routing_audit
import logging

logger = logging.getLogger(__name__)


class RoutingBenchmark:
    @staticmethod
    async def simulate(requirements: Dict[str, Any], mode: str = RoutingMode.AUTO) -> Dict[str, Any]:
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        if not registry:
            return {"status": "not_configured", "reason": "No model registry available"}

        candidates = []
        try:
            from app.services.model_capability_engine import ModelCapabilityEngine, CapabilityRequirement
            from app.services.canonical_provider_registry import CanonicalProviderRegistry
            canonical = CanonicalProviderRegistry()
            capability_engine = ModelCapabilityEngine(registry, canonical)
            req = CapabilityRequirement.from_dict(requirements)
            candidates = capability_engine.get_compatible_models(req)
        except Exception:
            pass

        return {
            "status": "simulated",
            "candidate_count": len(candidates),
            "candidates": [{"model_id": m.id, "provider_id": m.provider} for m, _ in candidates[:10]],
            "routing_mode": mode,
        }


routing_benchmark = RoutingBenchmark()
