from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Strategy:
    name: str
    success_probability: float = 0.5
    resource_cost: float = 1.0
    execution_time: float = 1.0
    quality_expectation: float = 0.5
    risk: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyEngine:
    def __init__(self) -> None:
        self._strategies: Dict[str, Strategy] = {}
        self._history: List[Dict[str, Any]] = []

    def register_strategy(self, strategy: Strategy) -> None:
        self._strategies[strategy.name] = strategy

    def score_strategy(self, strategy: Strategy, context: Dict[str, Any]) -> float:
        weights = {
            "success_probability": 0.4,
            "resource_cost": -0.2,
            "execution_time": -0.2,
            "quality_expectation": 0.3,
            "risk": -0.1,
        }
        score = 0.0
        for key, weight in weights.items():
            value = getattr(strategy, key, 0.5)
            score += weight * value
        return max(0.0, min(1.0, score))

    def select_best_strategy(self, context: Dict[str, Any]) -> Optional[Strategy]:
        if not self._strategies:
            return None
        scored = [(name, self.score_strategy(s, context)) for name, s in self._strategies.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return self._strategies.get(scored[0][0])

    def generate_alternatives(self, task: Any, plan: Any) -> List[str]:
        alternatives = []
        for name in self._strategies:
            if getattr(plan, "alternative_strategy", None) != name:
                alternatives.append(name)
        return alternatives[:3]
