"""
MAKE Autonomous Agent Core V2 — Observation Engine.

Inspects execution outputs and produces structured observations.
Does not fabricate observations.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime


class ObservationCategory(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    QUALITY = "quality"
    MISSING_REQUIREMENT = "missing_requirement"
    CONTRADICTION = "contradiction"
    VISUAL_MISMATCH = "visual_mismatch"
    SPECIFICATION_MISMATCH = "specification_mismatch"
    INCOMPLETE_ARTIFACT = "incomplete_artifact"
    TOOL_FAILURE = "tool_failure"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    NO_ARTIFACT = "no_artifact"


class ObservationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Observation:
    observation_id: UUID
    execution_id: UUID
    node_id: Optional[UUID]
    category: ObservationCategory
    severity: ObservationSeverity
    description: str
    evidence: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        execution_id: UUID,
        category: ObservationCategory,
        severity: ObservationSeverity,
        description: str,
        evidence: Optional[Dict[str, Any]] = None,
        node_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        return cls(
            observation_id=UUID(int=0),  # placeholder, set by engine
            execution_id=execution_id,
            node_id=node_id,
            category=category,
            severity=severity,
            description=description,
            evidence=evidence or {},
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": str(self.observation_id),
            "execution_id": str(self.execution_id),
            "node_id": str(self.node_id) if self.node_id else None,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class ObservationEngineV2:
    def __init__(self) -> None:
        self._observations: Dict[UUID, List[Observation]] = {}

    def record(
        self,
        execution_id: UUID,
        category: ObservationCategory,
        severity: ObservationSeverity,
        description: str,
        evidence: Optional[Dict[str, Any]] = None,
        node_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        observation = Observation.create(
            execution_id=execution_id,
            category=category,
            severity=severity,
            description=description,
            evidence=evidence,
            node_id=node_id,
            metadata=metadata,
        )
        # Assign stable ID deterministically based on content hash
        import hashlib
        content = f"{execution_id}:{category}:{severity}:{description}:{node_id}"
        observation.observation_id = UUID(hashlib.sha256(content.encode()).hexdigest()[:32])
        self._observations.setdefault(execution_id, []).append(observation)
        return observation

    def record_no_artifact(self, execution_id: UUID, node_id: UUID, tool_name: str) -> Observation:
        return self.record(
            execution_id=execution_id,
            category=ObservationCategory.NO_ARTIFACT,
            severity=ObservationSeverity.ERROR,
            description=f"Tool {tool_name} did not return an artifact for node {node_id}",
            evidence={"tool": tool_name, "node_id": str(node_id)},
            node_id=node_id,
        )

    def record_failure(self, execution_id: UUID, node_id: UUID, error: str, tool_name: str = "") -> Observation:
        return self.record(
            execution_id=execution_id,
            category=ObservationCategory.FAILURE,
            severity=ObservationSeverity.ERROR,
            description=error,
            evidence={"tool": tool_name, "node_id": str(node_id)},
            node_id=node_id,
        )

    def record_quality(self, execution_id: UUID, node_id: UUID, metric: str, value: Any, threshold: Any) -> Observation:
        passed = value >= threshold if isinstance(value, (int, float)) else False
        return self.record(
            execution_id=execution_id,
            category=ObservationCategory.QUALITY,
            severity=ObservationSeverity.INFO if passed else ObservationSeverity.WARNING,
            description=f"Quality metric {metric}: {value} (threshold: {threshold})",
            evidence={"metric": metric, "value": value, "threshold": threshold, "passed": passed},
            node_id=node_id,
        )

    def get_observations(self, execution_id: UUID) -> List[Observation]:
        return list(self._observations.get(execution_id, []))

    def get_by_category(self, execution_id: UUID, category: ObservationCategory) -> List[Observation]:
        return [o for o in self._observations.get(execution_id, []) if o.category == category]

    def has_failures(self, execution_id: UUID) -> bool:
        return any(
            o.category in (ObservationCategory.FAILURE, ObservationCategory.TOOL_FAILURE, ObservationCategory.INFRASTRUCTURE_FAILURE)
            for o in self._observations.get(execution_id, [])
        )
