"""MAKE Image Engine — Provenance System.

Tracks generation provenance for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class ProvenanceRecord:
    model_version: str = "make-image-v0.1.0"
    seed: int = 0
    prompt: str = ""
    conditioning_references: List[str] = field(default_factory=list)
    world_id: Optional[str] = None
    generation_config: Dict[str, Any] = field(default_factory=dict)
    resolution: Tuple[int, int] = (256, 256)
    sampler: str = "euler"
    inference_steps: int = 20
    timestamp: str = ""
    edit_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "seed": self.seed,
            "prompt": self.prompt,
            "conditioning_references": list(self.conditioning_references),
            "world_id": self.world_id,
            "generation_config": dict(self.generation_config),
            "resolution": list(self.resolution),
            "sampler": self.sampler,
            "inference_steps": self.inference_steps,
            "timestamp": self.timestamp,
            "edit_history": list(self.edit_history),
        }


class ProvenanceSystem:
    def __init__(self):
        self.records: List[ProvenanceRecord] = []

    def record(self, record: ProvenanceRecord) -> None:
        if not record.timestamp:
            record.timestamp = datetime.utcnow().isoformat() + "Z"
        self.records.append(record)

    def latest(self) -> Optional[ProvenanceRecord]:
        return self.records[-1] if self.records else None

    def to_json(self) -> str:
        import json
        return json.dumps([r.to_dict() for r in self.records], indent=2)


__all__ = [
    "ProvenanceRecord",
    "ProvenanceSystem",
]
