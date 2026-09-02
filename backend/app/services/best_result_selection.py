"""
Best Result Selection for MAKE AI Video Phase 16.

Ranks generation results based on user objective and selects the best.
"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class BestResultSelector:
    def __init__(self):
        pass

    def rank_results(self, results: List[Dict[str, Any]], objective: str = "general") -> List[Dict[str, Any]]:
        scored = []
        for result in results:
            score = self._calculate_score(result, objective)
            scored.append({**result, "rank_score": score})
        scored.sort(key=lambda x: x["rank_score"], reverse=True)
        return scored

    def _calculate_score(self, result: Dict[str, Any], objective: str) -> float:
        quality = result.get("quality_score", 0.0)
        validation = result.get("validation", {})
        valid = validation.get("valid", False)
        generation_time = result.get("generation_time", 0.0)
        cost = result.get("cost", 0.0)

        score = quality * 0.4
        if valid:
            score += 0.3
        if objective == "cinematic":
            score += result.get("cinematic_score", 0.0) * 0.2
        elif objective == "character":
            score += result.get("identity_score", 0.0) * 0.2
        elif objective == "product":
            score += result.get("product_score", 0.0) * 0.2
        elif objective == "speed":
            score += max(0, 1.0 - (generation_time / 60.0)) * 0.3
        elif objective == "cheap":
            score += max(0, 1.0 - cost) * 0.3

        return score

    def select_best(self, results: List[Dict[str, Any]], objective: str = "general") -> Optional[Dict[str, Any]]:
        ranked = self.rank_results(results, objective)
        return ranked[0] if ranked else None


best_result_selector = BestResultSelector()
