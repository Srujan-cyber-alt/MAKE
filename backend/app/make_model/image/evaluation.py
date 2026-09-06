"""MAKE Image Engine — Evaluation and Benchmarking.

Internal benchmark categories, fixed prompts, and human evaluation workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    references: List[str] = field(default_factory=list)
    conditioning: Dict[str, Any] = field(default_factory=dict)
    expected_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    name: str = "make-image-benchmark-v1"
    cases: List[BenchmarkCase] = field(default_factory=list)

    def add_case(self, case: BenchmarkCase) -> None:
        self.cases.append(case)

    def cases_by_category(self, category: str) -> List[BenchmarkCase]:
        return [c for c in self.cases if c.category == category]


@dataclass
class HumanEvaluationRecord:
    evaluator_id: str
    case_id: str
    scores: Dict[str, float] = field(default_factory=dict)
    preferred: str = ""
    notes: str = ""


class HumanEvaluationWorkflow:
    def __init__(self):
        self.records: List[HumanEvaluationRecord] = []

    def submit(self, record: HumanEvaluationRecord) -> None:
        self.records.append(record)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_evaluations": len(self.records),
            "evaluators": len({r.evaluator_id for r in self.records}),
            "cases": len({r.case_id for r in self.records}),
        }


class ImageBenchmark:
    def __init__(self):
        self.suite = BenchmarkSuite()
        self._populate_defaults()

    def _populate_defaults(self) -> None:
        categories = [
            "text_to_image", "photorealism", "human_realism", "identity", "hands",
            "objects", "materials", "lighting", "composition", "multi_reference",
            "editing", "inpainting", "outpainting", "world_consistency", "camera_control",
            "depth", "pose", "product", "architecture", "environments", "surreal", "high_resolution",
        ]
        for i, cat in enumerate(categories):
            self.suite.add_case(BenchmarkCase(
                case_id=f"{cat}_{i:03d}",
                category=cat,
                prompt=f"benchmark prompt for {cat}",
                expected_metrics={"realism": 0.7, "anatomy": 0.7, "detail": 0.5},
            ))

    def run(self, engine: Any) -> Dict[str, Any]:
        results = []
        for case in self.suite.cases:
            try:
                result = engine.run(case)
                results.append({"case_id": case.case_id, "ok": True, "result": result})
            except Exception as e:
                results.append({"case_id": case.case_id, "ok": False, "error": str(e)})
        return {"total": len(results), "passed": sum(1 for r in results if r.get("ok")), "failed": sum(1 for r in results if not r.get("ok")), "results": results}


__all__ = [
    "BenchmarkCase",
    "BenchmarkSuite",
    "HumanEvaluationRecord",
    "HumanEvaluationWorkflow",
    "ImageBenchmark",
]
