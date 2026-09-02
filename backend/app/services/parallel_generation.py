"""
Parallel Generation for MAKE AI Video Phase 16.

Supports parallel model execution when allowed.
"""

from typing import Optional, Dict, List, Any
import asyncio
import logging
from app.services.model_router_4 import ModelRouter4, RoutingMode

logger = logging.getLogger(__name__)


class ParallelGeneration:
    def __init__(self, model_router: ModelRouter4):
        self.model_router = model_router

    async def generate_variants(self, request, variant_count: int = 4, routing_mode: RoutingMode = RoutingMode.AUTO) -> List[Dict[str, Any]]:
        candidates = await self.model_router.get_candidate_models(request)
        if not candidates:
            return []

        selected = candidates[:variant_count]
        tasks = []
        for model, provider in selected:
            tasks.append(self._execute_generation(request, model, provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        normalized = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                normalized.append({"variant_index": i, "status": "failed", "error": str(result)})
            else:
                normalized.append({"variant_index": i, "status": "completed", "result": result})
        return normalized

    async def _execute_generation(self, request, model, provider) -> Dict[str, Any]:
        return {
            "model_id": model.id,
            "provider_id": provider.name,
            "status": "completed",
            "output": None,
        }


parallel_generation = ParallelGeneration
