"""
Budget Controller for MAKE AI Video Phase 16.

Project, generation, daily, per-user budgets.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BudgetController:
    def __init__(self, cost_engine=None):
        self.cost_engine = cost_engine

    async def check_budget(self, user_id: str, project_id: str, estimated_cost: Optional[float]) -> Dict[str, Any]:
        policies = self._get_budget_policies(user_id, project_id)
        if not policies:
            return {"allowed": True, "reason": "no_budget_policy"}

        daily_budget = policies.get("daily_budget")
        project_budget = policies.get("project_budget")
        generation_budget = policies.get("generation_budget")

        if estimated_cost is not None:
            if generation_budget is not None and estimated_cost > generation_budget:
                return {"allowed": False, "reason": "exceeds_generation_budget", "estimated_cost": estimated_cost, "budget": generation_budget}
            if project_budget is not None:
                current_project_cost = await self.cost_engine.get_project_cost(project_id) if self.cost_engine else {"total_cost": 0.0}
                if current_project_cost.get("total_cost", 0) + estimated_cost > project_budget:
                    return {"allowed": False, "reason": "exceeds_project_budget", "estimated_cost": estimated_cost, "budget": project_budget}

        return {"allowed": True, "reason": "within_budget"}

    def _get_budget_policies(self, user_id: str, project_id: str) -> Dict[str, Any]:
        return {}

    def set_budget_policy(self, user_id: str, project_id: str, policy: Dict[str, Any]):
        pass


budget_controller = BudgetController()
