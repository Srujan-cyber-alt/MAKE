"""
Budget Intelligence for MAKE AI Video Phase 19.

Extends Phase 16 BudgetController with shot-level allocation and repair reserves.
"""

from typing import Optional, Dict, List, Any
from app.services.budget_controller import budget_controller
import logging

logger = logging.getLogger(__name__)


class BudgetIntelligence:
    @staticmethod
    async def allocate(shots: List[Dict[str, Any]], total_budget: Optional[float], repair_reserve_ratio: float = 0.3) -> Dict[str, Any]:
        if total_budget is None:
            return {"allocated": {}, "repair_reserve": 0.0, "mode": "unlimited"}

        repair_reserve = total_budget * repair_reserve_ratio
        generation_budget = total_budget - repair_reserve
        shot_count = len(shots)
        if shot_count == 0:
            return {"allocated": {}, "repair_reserve": repair_reserve, "mode": "per_shot"}

        per_shot_base = generation_budget / shot_count
        allocated = {}
        for shot in shots:
            shot_id = shot.get("shot_id", "unknown")
            priority_multiplier = 1.0
            if shot.get("priority") == "hero":
                priority_multiplier = 2.5
            elif shot.get("priority") == "high":
                priority_multiplier = 1.5
            elif shot.get("priority") == "low":
                priority_multiplier = 0.5
            allocated[shot_id] = {
                "budget": per_shot_base * priority_multiplier,
                "repair_budget": per_shot_base * priority_multiplier * repair_reserve_ratio,
                "priority_multiplier": priority_multiplier,
            }
        return {"allocated": allocated, "repair_reserve": repair_reserve, "mode": "per_shot"}

    @staticmethod
    async def check_shot_budget(shot_id: str, estimated_cost: Optional[float], allocation: Dict[str, Any]) -> Dict[str, Any]:
        if estimated_cost is None:
            return {"allowed": True, "reason": "cost_unknown"}
        shot_budget = allocation.get("allocated", {}).get(shot_id, {}).get("budget")
        if shot_budget is None:
            return {"allowed": True, "reason": "no_allocation"}
        if estimated_cost > shot_budget:
            return {"allowed": False, "reason": "exceeds_shot_budget", "estimated_cost": estimated_cost, "budget": shot_budget}
        return {"allowed": True, "reason": "within_shot_budget"}


budget_intelligence = BudgetIntelligence()
