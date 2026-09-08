"""
MAKE Autonomous Agent Core V2 — Execution Graph.

Persistent, versioned execution graph with full provenance.
Each node has stable ID, type, state, timestamps, parent, dependencies,
inputs, outputs, provenance, retry count, and error information.

Execution states:
  CREATED, QUEUED, PLANNING, READY, RUNNING, WAITING,
  CHECKPOINTED, OBSERVING, CRITIQUING, REVISING, COMPLETED,
  FAILED, CANCELLED
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
from datetime import datetime


class ExecutionState(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    CHECKPOINTED = "checkpointed"
    OBSERVING = "observing"
    CRITIQUING = "critiquing"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, Enum):
    INTENT = "intent"
    CONSTRAINTS = "constraints"
    ENTITIES = "entities"
    PLAN = "plan"
    TASK = "task"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    CRITIQUE = "critique"
    REVISION = "revision"
    ARTIFACT = "artifact"
    CHECKPOINT = "checkpoint"
    QUALITY_DECISION = "quality_decision"
    VALIDATION = "validation"
    APPROVAL = "approval"
    COMPLETION = "completion"


@dataclass
class ExecutionNode:
    node_id: UUID
    node_type: NodeType
    state: ExecutionState
    parent_id: Optional[UUID]
    dependency_ids: List[UUID]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    provenance: Dict[str, Any]
    retry_count: int
    error_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    execution_id: UUID
    branch: str = "main"

    @classmethod
    def create(
        cls,
        node_type: NodeType,
        execution_id: UUID,
        parent_id: Optional[UUID] = None,
        dependency_ids: Optional[List[UUID]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        branch: str = "main",
    ) -> ExecutionNode:
        now = datetime.utcnow()
        return cls(
            node_id=uuid4(),
            node_type=node_type,
            state=ExecutionState.CREATED,
            parent_id=parent_id,
            dependency_ids=dependency_ids or [],
            inputs=inputs or {},
            outputs={},
            provenance={"created_by": "execution_graph", "created_at": now.isoformat()},
            retry_count=0,
            error_info=None,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            execution_id=execution_id,
            branch=branch,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "state": self.state.value,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "dependency_ids": [str(d) for d in self.dependency_ids],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "provenance": self.provenance,
            "retry_count": self.retry_count,
            "error_info": self.error_info,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "execution_id": str(self.execution_id),
            "branch": self.branch,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionNode:
        return cls(
            node_id=UUID(data["node_id"]),
            node_type=NodeType(data["node_type"]),
            state=ExecutionState(data["state"]),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            dependency_ids=[UUID(d) for d in data.get("dependency_ids", [])],
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            provenance=data.get("provenance", {}),
            retry_count=data.get("retry_count", 0),
            error_info=data.get("error_info"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            execution_id=UUID(data["execution_id"]),
            branch=data.get("branch", "main"),
        )


@dataclass
class ExecutionGraph:
    execution_id: UUID
    root_node_id: Optional[UUID]
    nodes: Dict[UUID, ExecutionNode]
    edges: Dict[UUID, Set[UUID]]
    created_at: datetime
    updated_at: datetime
    completed: bool = False
    final_artifact_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, execution_id: Optional[UUID] = None) -> ExecutionGraph:
        eid = execution_id or uuid4()
        now = datetime.utcnow()
        return cls(
            execution_id=eid,
            root_node_id=None,
            nodes={},
            edges={},
            created_at=now,
            updated_at=now,
        )

    def add_node(self, node: ExecutionNode) -> None:
        if self._would_create_cycle(node):
            raise ValueError(f"Adding node {node.node_id} would create a cycle")
        self.nodes[node.node_id] = node
        if self.root_node_id is None:
            self.root_node_id = node.node_id
        for dep_id in node.dependency_ids:
            self.edges.setdefault(dep_id, set()).add(node.node_id)
        self.updated_at = datetime.utcnow()

    def _would_create_cycle(self, new_node: ExecutionNode) -> bool:
        if new_node.node_id in new_node.dependency_ids:
            return True
        visited: set = set()
        stack = list(new_node.dependency_ids)
        while stack:
            current = stack.pop()
            if current == new_node.node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            if current in self.nodes:
                node = self.nodes[current]
                stack.extend(node.dependency_ids)
        return False

    def get_node(self, node_id: UUID) -> Optional[ExecutionNode]:
        return self.nodes.get(node_id)

    def get_children(self, node_id: UUID) -> List[ExecutionNode]:
        child_ids = self.edges.get(node_id, set())
        return [self.nodes[cid] for cid in child_ids if cid in self.nodes]

    def get_dependencies(self, node_id: UUID) -> List[ExecutionNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[did] for did in node.dependency_ids if did in self.nodes]

    def update_node_state(self, node_id: UUID, state: ExecutionState, outputs: Optional[Dict[str, Any]] = None, error_info: Optional[Dict[str, Any]] = None) -> None:
        node = self.nodes.get(node_id)
        if not node:
            raise KeyError(f"Node {node_id} not found")
        node.state = state
        node.updated_at = datetime.utcnow()
        if outputs is not None:
            node.outputs = outputs
        if error_info is not None:
            node.error_info = error_info
        self.updated_at = datetime.utcnow()

    def get_ready_nodes(self) -> List[ExecutionNode]:
        ready = []
        for node in self.nodes.values():
            if node.state != ExecutionState.CREATED and node.state != ExecutionState.QUEUED:
                continue
            deps = self.get_dependencies(node.node_id)
            if all(d.state == ExecutionState.COMPLETED for d in deps):
                ready.append(node)
        return ready

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": str(self.execution_id),
            "root_node_id": str(self.root_node_id) if self.root_node_id else None,
            "nodes": {str(k): v.to_dict() for k, v in self.nodes.items()},
            "edges": {str(k): [str(v) for v in vs] for k, vs in self.edges.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed": self.completed,
            "final_artifact_id": str(self.final_artifact_id) if self.final_artifact_id else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionGraph:
        graph = cls(
            execution_id=UUID(data["execution_id"]),
            root_node_id=UUID(data["root_node_id"]) if data.get("root_node_id") else None,
            nodes={},
            edges={},
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed=data.get("completed", False),
            final_artifact_id=UUID(data["final_artifact_id"]) if data.get("final_artifact_id") else None,
            metadata=data.get("metadata", {}),
        )
        for node_id_str, node_data in data.get("nodes", {}).items():
            node = ExecutionNode.from_dict(node_data)
            graph.nodes[node.node_id] = node
        for node_id_str, child_ids in data.get("edges", {}).items():
            graph.edges[UUID(node_id_str)] = {UUID(c) for c in child_ids}
        return graph
