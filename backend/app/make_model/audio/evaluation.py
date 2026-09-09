"""
Audio evaluation engine - batch quality evaluation and metrics aggregation.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from app.make_model.audio.quality import AudioQualityEvaluator


class AudioEvaluationEngine:
    def __init__(self) -> None:
        self._evaluator = AudioQualityEvaluator()
        self._history: List[Dict[str, Any]] = []

    async def evaluate(self, audio_path: str) -> Dict[str, Any]:
        report = await self._evaluator.evaluate(audio_path)
        result = {
            "audio_path": audio_path,
            "snr_db": report.snr_db,
            "clipping_ratio": report.clipping_ratio,
            "silence_ratio": report.silence_ratio,
            "spectral_stability": report.spectral_stability,
            "overall_score": report.overall_score,
            "passed": report.passed,
        }
        self._history.append(result)
        return result

    async def evaluate_batch(self, audio_paths: List[str]) -> List[Dict[str, Any]]:
        results = []
        for path in audio_paths:
            result = await self.evaluate(path)
            results.append(result)
        return results

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def get_pass_rate(self) -> float:
        if not self._history:
            return 0.0
        passed = sum(1 for r in self._history if r["passed"])
        return passed / len(self._history)
