from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    strategy_hash: str
    task_type: str
    success: bool
    score: float
    duration_ms: float
    resource_cost: Optional[Dict[str, Any]] = None
    failure_category: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class StrategyOutcome:
    SUCCESS = "success"
    FAILURE = "failure"


class DecisionMemory:
    def __init__(self) -> None:
        self._memory: Dict[str, List[MemoryEntry]] = {}

    def record(
        self,
        strategy_hash: str,
        task_type: str,
        success: bool,
        score: float,
        duration_ms: float,
        resource_cost: Optional[Dict[str, Any]] = None,
        failure_category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = MemoryEntry(
            strategy_hash=strategy_hash,
            task_type=task_type,
            success=success,
            score=score,
            duration_ms=duration_ms,
            resource_cost=resource_cost,
            failure_category=failure_category,
            context=context,
            metadata=metadata,
        )
        self._memory.setdefault(strategy_hash, []).append(entry)

    def get_history(self, strategy_hash: str) -> List[MemoryEntry]:
        return list(self._memory.get(strategy_hash, []))

    def recommend(self, task_type: str) -> Optional[str]:
        best_strategy = None
        best_score = -1.0
        for strategy_hash, entries in self._memory.items():
            relevant = [e for e in entries if e.task_type == task_type and e.success]
            if relevant:
                avg_score = sum(e.score for e in relevant) / len(relevant)
                if avg_score > best_score:
                    best_score = avg_score
                    best_strategy = strategy_hash
        return best_strategy

    def search_by_task_type(self, task_type: str) -> List[MemoryEntry]:
        results = []
        for entries in self._memory.values():
            for entry in entries:
                if entry.task_type == task_type:
                    results.append(entry)
        return results

    def search_by_result(self, success: bool) -> List[MemoryEntry]:
        results = []
        for entries in self._memory.values():
            for entry in entries:
                if entry.success == success:
                    results.append(entry)
        return results
