"""Curriculum learning + hard-example mining for MAKE World Model X.

Curriculum stages are *configurable*, not hard-coded. The default 10
stages follow a simple -> complex progression, but each stage can be
overridden at runtime.

Hard-example mining reads the failure classification produced by
MAKE's existing FailureIntelligence and turns it into upweighted
sampling probabilities.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.make_model.world.data_engine import DatasetManifest, TrainingSample


# ----------------------------------------------------------------------
# Curriculum
# ----------------------------------------------------------------------


@dataclass
class CurriculumStage:
    """A single curriculum stage.

    A stage is "passed" when at least `min_samples` samples satisfy
    the quality predicate AND at least `min_coverage` of the dataset
    has been seen at least once.
    """

    name: str
    description: str
    min_sharpness: float = 0.05
    min_motion: float = 0.01
    max_black_ratio: float = 0.30
    min_resolution: int = 32
    min_samples: int = 100
    min_coverage: float = 0.5
    duration_minutes: int = 60


DEFAULT_STAGES: List[CurriculumStage] = [
    CurriculumStage(
        name="stage1_clean_motion",
        description="Simple motion / clean clips",
        min_sharpness=0.10,
        min_motion=0.03,
        max_black_ratio=0.10,
        min_resolution=32,
    ),
    CurriculumStage(
        name="stage2_basic_actions",
        description="Basic actions / scenes",
        min_sharpness=0.08,
        min_motion=0.04,
        min_resolution=32,
    ),
    CurriculumStage(
        name="stage3_complex_camera",
        description="Complex camera movement",
        min_sharpness=0.08,
        min_motion=0.05,
        min_resolution=32,
    ),
    CurriculumStage(
        name="stage4_humans",
        description="Human interactions",
        min_sharpness=0.10,
        min_motion=0.03,
        min_resolution=48,
    ),
    CurriculumStage(
        name="stage5_objects",
        description="Object interactions",
        min_sharpness=0.10,
        min_motion=0.03,
        min_resolution=48,
    ),
    CurriculumStage(
        name="stage6_environments",
        description="Complex environments",
        min_sharpness=0.08,
        min_motion=0.02,
        min_resolution=64,
    ),
    CurriculumStage(
        name="stage7_cinematic",
        description="Cinematic sequences",
        min_sharpness=0.10,
        min_motion=0.04,
        min_resolution=64,
    ),
    CurriculumStage(
        name="stage8_long_temporal",
        description="Longer temporal relationships",
        min_sharpness=0.08,
        min_motion=0.04,
        min_resolution=64,
    ),
    CurriculumStage(
        name="stage9_multimodal",
        description="Complex multimodal conditioning",
        min_sharpness=0.10,
        min_motion=0.03,
        min_resolution=64,
    ),
    CurriculumStage(
        name="stage10_hard",
        description="Hard examples (mined from failure set)",
        min_sharpness=0.05,
        min_motion=0.02,
        min_resolution=64,
    ),
]


@dataclass
class Curriculum:
    stages: List[CurriculumStage] = field(default_factory=lambda: list(DEFAULT_STAGES))
    current_stage_index: int = 0

    def current(self) -> CurriculumStage:
        return self.stages[self.current_stage_index]

    def advance(self) -> bool:
        if self.current_stage_index + 1 < len(self.stages):
            self.current_stage_index += 1
            return True
        return False

    def filter_samples(self, samples: Sequence[TrainingSample]) -> List[TrainingSample]:
        s = self.current()
        out: List[TrainingSample] = []
        for x in samples:
            if x.split != "train":
                continue
            if x.quality.sharpness < s.min_sharpness:
                continue
            if x.quality.motion < s.min_motion:
                continue
            if x.quality.black_frame_ratio > s.max_black_ratio:
                continue
            if min(x.width, x.height) < s.min_resolution:
                continue
            out.append(x)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_stage_index": self.current_stage_index,
            "stages": [asdict(s) for s in self.stages],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Curriculum":
        stages = [CurriculumStage(**s) for s in d["stages"]]
        return cls(stages=stages, current_stage_index=d.get("current_stage_index", 0))


# ----------------------------------------------------------------------
# Hard-example mining
# ----------------------------------------------------------------------


@dataclass
class FailureRecord:
    """A single failure classified by MAKE's existing FailureIntelligence.

    The model side only consumes the summary; the classification itself
    lives in the existing service.
    """

    sample_id: str
    failure_class: str       # motion | identity | object | camera | artifact | prompt | physics | scene
    severity: float          # 0..1
    notes: str = ""


@dataclass
class HardExampleSet:
    failures: List[FailureRecord] = field(default_factory=list)

    def add(self, rec: FailureRecord) -> None:
        self.failures.append(rec)

    def ids(self) -> List[str]:
        return [f.sample_id for f in self.failures]

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.failures], f, indent=2)

    @classmethod
    def load(cls, path: str) -> "HardExampleSet":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(failures=[FailureRecord(**r) for r in data])


class WeightedSampler:
    """Sample training items with upweighting for hard examples.

    Hard examples are sampled `hard_multiplier` more often than
    non-hard examples. The class does not require torch; the
    training loop translates the resulting indices into a batch.
    """

    def __init__(self, hard_multiplier: float = 3.0, seed: int = 0) -> None:
        self.hard_multiplier = hard_multiplier
        self.seed = seed
        self._rng = random.Random(seed)

    def weights(
        self,
        samples: Sequence[TrainingSample],
        hard_ids: Sequence[str],
    ) -> List[float]:
        hset = set(hard_ids)
        w: List[float] = []
        for s in samples:
            base = max(float(s.quality.motion), 0.01)
            if s.sample_id in hset:
                base *= self.hard_multiplier
            w.append(base)
        s_total = sum(w)
        if s_total <= 0:
            return [1.0 / max(len(samples), 1)] * len(samples)
        return [x / s_total for x in w]

    def draw(
        self,
        samples: Sequence[TrainingSample],
        hard_ids: Sequence[str],
        batch_size: int,
    ) -> List[TrainingSample]:
        w = self.weights(samples, hard_ids)
        # numpy random choice
        import numpy as np
        idx = np.random.choice(len(samples), size=batch_size, replace=True, p=np.array(w))
        return [samples[int(i)] for i in idx]


__all__ = [
    "CurriculumStage",
    "Curriculum",
    "DEFAULT_STAGES",
    "FailureRecord",
    "HardExampleSet",
    "WeightedSampler",
]
