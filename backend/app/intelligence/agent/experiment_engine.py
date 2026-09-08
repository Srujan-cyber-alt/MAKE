from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class ExperimentVariant:
    name: str
    strategy: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    experiment_id: UUID
    winner: Optional[str]
    results: Dict[str, Any]
    metrics: Dict[str, Any]
    evidence: Dict[str, Any]


@dataclass
class Experiment:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    hypothesis: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    variants: List[ExperimentVariant] = field(default_factory=list)
    status: str = "created"
    result: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class ExperimentEngine:
    def __init__(self) -> None:
        self._experiments: Dict[UUID, Experiment] = {}
        self._results: Dict[UUID, ExperimentResult] = {}

    def create_experiment(
        self,
        name: str,
        hypothesis: str,
        variants: List[ExperimentVariant],
        variables: Optional[Dict[str, Any]] = None,
    ) -> Experiment:
        experiment = Experiment(
            name=name,
            hypothesis=hypothesis,
            variants=variants,
            variables=variables,
        )
        self._experiments[experiment.id] = experiment
        return experiment

    def run_experiment(self, experiment: Experiment) -> ExperimentResult:
        if not experiment.variants:
            raise ValueError("Experiment must have at least one variant")
        results = {}
        metrics = {}
        for variant in experiment.variants:
            result = self._execute_variant(variant)
            results[variant.name] = result
            metrics[variant.name] = {"score": result.get("score", 0.0), "duration": result.get("duration", 0.0)}
        best_variant = max(metrics, key=lambda k: metrics[k].get("score", 0.0))
        experiment.result = best_variant
        experiment.metrics = metrics
        experiment.evidence = results
        experiment.status = "completed"
        result = ExperimentResult(
            experiment_id=experiment.id,
            winner=best_variant,
            results=results,
            metrics=metrics,
            evidence=results,
        )
        self._results[experiment.id] = result
        return result

    def _execute_variant(self, variant: ExperimentVariant) -> Dict[str, Any]:
        import random
        return {
            "score": random.uniform(0.5, 1.0),
            "duration": random.uniform(0.1, 5.0),
            "success": random.random() > 0.2,
        }

    def get_winner(self, experiment: Experiment) -> Optional[str]:
        return experiment.result
