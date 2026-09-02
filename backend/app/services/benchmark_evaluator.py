"""
Benchmark Evaluator for MAKE AI Video Phase 20.

Evaluates benchmark results using existing quality infrastructure.
"""

from typing import Optional, List, Dict, Any
from app.services.cinematic_quality_score import cinematic_quality_score
from app.services.artifact_detector import artifact_detector
from app.services.failure_classifier import failure_classifier
from app.services.cost_engine import cost_engine
from app.services.model_performance_memory import model_performance_memory
from app.services.generation_learning import GenerationLearning
import logging

logger = logging.getLogger(__name__)


class BenchmarkEvaluator:
    @staticmethod
    def evaluate_case(case_result: Dict[str, Any]) -> Dict[str, Any]:
        results = case_result.get("results", [])
        evaluated = []
        for res in results:
            evaluation = BenchmarkEvaluator._evaluate_single(res)
            evaluated.append(evaluation)
        return {
            "case_id": case_result.get("case_id"),
            "task_type": case_result.get("task_type"),
            "evaluated_results": evaluated,
            "best_result": BenchmarkEvaluator._select_best(evaluated),
            "summary": BenchmarkEvaluator._summarize_case(evaluated),
        }

    @staticmethod
    def _evaluate_single(result: Dict[str, Any]) -> Dict[str, Any]:
        quality = result.get("quality_score") or {}
        technical = result.get("technical_validation") or {}
        overall_score = quality.get("overall", 0.0)
        technical_score = technical.get("overall_score", 0.0)

        analysis = {
            "face_drift": False,
            "identity_drift": False,
            "product_drift": False,
            "temporal_flicker": False,
            "lighting_jump": False,
            "camera_instability": False,
            "motion_artifacts": False,
            "overall_score": overall_score,
        }
        artifacts = artifact_detector.classify(analysis)

        failure_type = failure_classifier.classify(None, analysis)
        failure_policy = failure_classifier.get_policy(failure_type)

        cost = result.get("cost")
        latency = result.get("duration")

        return {
            "generation_id": result.get("generation_id"),
            "model": result.get("model"),
            "provider": result.get("provider"),
            "status": result.get("status"),
            "overall_score": overall_score,
            "technical_score": technical_score,
            "artifacts": artifacts,
            "artifact_count": len(artifacts),
            "failure_type": failure_type.value if failure_type else None,
            "retryable": failure_policy.retryable if failure_policy else False,
            "fallback_allowed": failure_policy.fallback_allowed if failure_policy else False,
            "cost": cost,
            "latency": latency,
            "passed": overall_score >= 0.7 and technical_score >= 0.7,
        }

    @staticmethod
    def _select_best(evaluated: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not evaluated:
            return None
        scored = [(e, e.get("overall_score", 0.0)) for e in evaluated]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    @staticmethod
    def _summarize_case(evaluated: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not evaluated:
            return {"total": 0, "passed": 0, "failed": 0, "avg_score": 0.0}
        passed = sum(1 for e in evaluated if e.get("passed"))
        scores = [e.get("overall_score", 0.0) for e in evaluated]
        return {
            "total": len(evaluated),
            "passed": passed,
            "failed": len(evaluated) - passed,
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "best_score": max(scores) if scores else 0.0,
        }


benchmark_evaluator = BenchmarkEvaluator()
