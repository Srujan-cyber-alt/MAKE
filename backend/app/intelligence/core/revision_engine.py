"""
MAKE Autonomous Agent Core V2 — Revision Engine.

Handles autonomous revision when quality decision is REVISE.
Preserves successful components, creates new execution branch.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState
from app.intelligence.core.quality_decision import QualityDecision


class RevisionStrategy(str, Enum):
    RETRY_TOOL = "retry_tool"
    MODIFY_PARAMETERS = "modify_parameters"
    DECOMPOSE_FURTHER = "decompose_further"
    ALTERNATE_TOOL = "alternate_tool"
    ADD_REQUIREMENT = "add_requirement"
    REDUCE_SCOPE = "reduce_scope"


@dataclass
class RevisionPlan:
    revision_id: UUID
    parent_execution_id: UUID
    new_execution_id: UUID
    strategy: RevisionStrategy
    reason: str
    evidence: Dict[str, Any]
    changed_constraints: Dict[str, Any]
    changed_plan: Dict[str, Any]
    preserved_components: List[UUID]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revision_id": str(self.revision_id),
            "parent_execution_id": str(self.parent_execution_id),
            "new_execution_id": str(self.new_execution_id),
            "strategy": self.strategy.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "changed_constraints": self.changed_constraints,
            "changed_plan": self.changed_plan,
            "preserved_components": [str(c) for c in self.preserved_components],
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class RevisionEngine:
    def __init__(self) -> None:
        self._revisions: Dict[UUID, List[RevisionPlan]] = {}

    def create_revision(
        self,
        parent_execution_id: UUID,
        new_execution_id: UUID,
        strategy: RevisionStrategy,
        reason: str,
        evidence: Dict[str, Any],
        changed_constraints: Optional[Dict[str, Any]] = None,
        changed_plan: Optional[Dict[str, Any]] = None,
        preserved_components: Optional[List[UUID]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RevisionPlan:
        revision = RevisionPlan(
            revision_id=UUID(int=0),
            parent_execution_id=parent_execution_id,
            new_execution_id=new_execution_id,
            strategy=strategy,
            reason=reason,
            evidence=evidence,
            changed_constraints=changed_constraints or {},
            changed_plan=changed_plan or {},
            preserved_components=preserved_components or [],
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        import hashlib
        content = f"{parent_execution_id}:{new_execution_id}:{strategy}:{reason}"
        revision.revision_id = UUID(hashlib.sha256(content.encode()).hexdigest()[:32])
        self._revisions.setdefault(parent_execution_id, []).append(revision)
        return revision

    def get_revisions(self, execution_id: UUID) -> List[RevisionPlan]:
        return list(self._revisions.get(execution_id, []))

    def apply_revision_to_graph(self, graph: ExecutionGraph, revision: RevisionPlan) -> ExecutionGraph:
        new_graph = ExecutionGraph.create(execution_id=revision.new_execution_id)
        # Preserve completed nodes from parent graph
        for node in graph.nodes.values():
            if node.state == ExecutionState.COMPLETED and node.node_id in revision.preserved_components:
                new_graph.add_node(node)
            elif node.node_id in revision.preserved_components:
                new_graph.add_node(node)
        return new_graph
