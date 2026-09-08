"""
Audio evaluation - comprehensive quality and performance evaluation.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from app.make_model.audio.quality import AudioQualityEvaluator
from app.make_model.audio.types import QualityReport


class AudioEvaluationEngine:
    def __init__(self) -> None:
        self._evaluator = AudioQualityEvaluator()
        self._history: List[Dict[str, Any]] = []

    async def evaluate_generation(self, audio_path: str, expected_duration: Optional[float] = None) -> Dict[str, Any]:
        quality = await self._evaluator.evaluate(audio_path)
        result = {
            "audio_path": audio_path,
            "quality": quality.__dict__,
            "passed": quality.passed,
            "timestamp": time.time(),
        }
        if expected_duration:
            result["duration_match"] = abs(quality.details.get("duration_seconds", 0) - expected_duration) < 0.5
        self._history.append(result)
        return result

    async def evaluate_model(self, model_id: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in test_cases:
            result = await self.evaluate_generation(
                case.get("audio_path", ""),
                case.get("expected_duration"),
            )
            results.append(result)
        passed = sum(1 for r in results if r["passed"])
        return {
            "model_id": model_id,
            "total_cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": passed / len(results) if results else 0.0,
            "results": results,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)
