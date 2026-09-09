"""
Autonomous Self-Critique Loop.

PLAN → GENERATE → OBSERVE → QUALITY CHECK → CRITIQUE → REVISE → RECHECK → FINALIZE

Maximum retries configurable. Never loops infinitely. Stores every decision.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class CritiqueDecision(Enum):
    ACCEPT = "accept"
    REVISE = "revise"
    FAIL = "fail"


@dataclass
class CritiqueStep:
    step_name: str
    decision: CritiqueDecision
    metrics: Dict[str, Any]
    reasoning: str
    revisions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CritiqueResult:
    final_audio: np.ndarray
    steps: List[CritiqueStep]
    final_decision: CritiqueDecision
    retry_count: int
    provenance: Dict[str, Any]


class SelfCritiqueLoop:
    def __init__(self, max_retries: int = 3, quality_check_fn: Optional[Callable] = None):
        self.max_retries = max_retries
        self.quality_check_fn = quality_check_fn
        self.step_history: List[CritiqueStep] = []

    def evaluate_quality(self, audio: np.ndarray) -> Dict[str, Any]:
        if self.quality_check_fn:
            return self.quality_check_fn(audio)
        metrics = {}
        metrics["snr"] = float(10 * np.log10(np.mean(audio ** 2) / (np.var(audio) + 1e-10)))
        metrics["rms"] = float(np.sqrt(np.mean(audio ** 2)))
        metrics["peak"] = float(np.max(np.abs(audio)))
        metrics["clipping_ratio"] = float(np.mean(np.abs(audio) > 0.99))
        metrics["dc_offset"] = float(np.mean(audio))
        metrics["crest_factor"] = float(np.max(np.abs(audio)) / (np.sqrt(np.mean(audio ** 2)) + 1e-10))
        if metrics["clipping_ratio"] > 0.01:
            metrics["score"] = "FAIL"
        elif metrics["snr"] < 15:
            metrics["score"] = "REVISE"
        else:
            metrics["score"] = "PASS"
        return metrics

    def critique(self, audio: np.ndarray, metrics: Dict[str, Any], attempt: int) -> CritiqueStep:
        score = metrics.get("score", "PASS")
        if score == "PASS":
            decision = CritiqueDecision.ACCEPT
            reasoning = "Quality metrics within acceptable thresholds"
        elif score == "FAIL" and attempt < self.max_retries:
            decision = CritiqueDecision.REVISE
            reasoning = "Quality issue detected; revision required"
        else:
            decision = CritiqueDecision.FAIL
            reasoning = "Quality metrics failed after maximum retries"
        step = CritiqueStep(
            step_name=f"critique_attempt_{attempt}",
            decision=decision,
            metrics=metrics,
            reasoning=reasoning,
        )
        self.step_history.append(step)
        return step

    def revise(self, audio: np.ndarray, critique: CritiqueStep) -> np.ndarray:
        result = audio.copy()
        revisions = {}
        if "clipping_ratio" in critique.metrics and critique.metrics["clipping_ratio"] > 0.01:
            result = np.clip(result, -0.95, 0.95)
            revisions["clipping_repair"] = True
        if "dc_offset" in critique.metrics and abs(critique.metrics["dc_offset"]) > 0.01:
            result = result - np.mean(result)
            revisions["dc_removal"] = True
        if "crest_factor" in critique.metrics and critique.metrics["crest_factor"] > 12:
            max_val = np.max(np.abs(result))
            if max_val > 0:
                target_rms = max_val / 6.0
                current_rms = np.sqrt(np.mean(result ** 2))
                if current_rms > 0:
                    gain = target_rms / current_rms
                    result = np.clip(result * gain, -0.99, 0.99)
                revisions["crest_compression"] = True
        critique.revisions = revisions
        return result

    def run(
        self,
        plan_fn: Callable,
        generate_fn: Callable,
        observe_fn: Optional[Callable] = None,
    ) -> CritiqueResult:
        steps: List[CritiqueStep] = []
        plan_result = plan_fn()
        steps.append(CritiqueStep(
            step_name="plan",
            decision=CritiqueDecision.ACCEPT,
            metrics={"plan_result": str(type(plan_result))},
            reasoning="Plan phase completed",
        ))
        audio = generate_fn()
        steps.append(CritiqueStep(
            step_name="generate",
            decision=CritiqueDecision.ACCEPT,
            metrics={"samples": len(audio), "duration_s": len(audio) / 16000},
            reasoning="Initial generation completed",
        ))
        for attempt in range(1, self.max_retries + 1):
            if observe_fn:
                observe_fn(audio, attempt)
            metrics = self.evaluate_quality(audio)
            critique = self.critique(audio, metrics, attempt)
            steps.append(critique)
            if critique.decision == CritiqueDecision.ACCEPT:
                final_step = CritiqueStep(
                    step_name="finalize",
                    decision=CritiqueDecision.ACCEPT,
                    metrics=metrics,
                    reasoning="Finalized after acceptance",
                )
                steps.append(final_step)
                return CritiqueResult(
                    final_audio=audio,
                    steps=steps,
                    final_decision=CritiqueDecision.ACCEPT,
                    retry_count=attempt,
                    provenance={"method": "self_critique", "max_retries": self.max_retries, "steps": [s.step_name for s in steps]},
                )
            elif critique.decision == CritiqueDecision.REVISE:
                audio = self.revise(audio, critique)
            elif critique.decision == CritiqueDecision.FAIL:
                if attempt >= self.max_retries:
                    return CritiqueResult(
                        final_audio=audio,
                        steps=steps,
                        final_decision=CritiqueDecision.FAIL,
                        retry_count=attempt,
                        provenance={"method": "self_critique", "max_retries": self.max_retries, "steps": [s.step_name for s in steps]},
                    )
        return CritiqueResult(
            final_audio=audio,
            steps=steps,
            final_decision=CritiqueDecision.ACCEPT,
            retry_count=self.max_retries,
            provenance={"method": "self_critique", "max_retries": self.max_retries, "steps": [s.step_name for s in steps]},
        )
