"""
Model Leaderboard for MAKE AI Video Phase 20.

Ranks models based on benchmark and production evidence.
"""

from typing import Optional, List, Dict, Any
from app.services.model_performance_memory import model_performance_memory
from app.services.generation_learning import GenerationLearning
import logging

logger = logging.getLogger(__name__)


class ModelLeaderboard:
    @staticmethod
    async def build_leaderboard(task_type: str = "general", limit: int = 10) -> List[Dict[str, Any]]:
        return await model_performance_memory.get_best_models_for_task(task_type, limit)

    @staticmethod
    async def get_model_card(model_id: str, provider_id: str) -> Dict[str, Any]:
        stats = await model_performance_memory.get_model_stats(model_id, provider_id)
        return {
            "model_id": model_id,
            "provider_id": provider_id,
            "stats": stats,
            "sample_count": stats.get("total_generations", 0),
            "confidence": "high" if stats.get("total_generations", 0) >= 10 else "medium" if stats.get("total_generations", 0) >= 3 else "low",
        }


model_leaderboard = ModelLeaderboard()
