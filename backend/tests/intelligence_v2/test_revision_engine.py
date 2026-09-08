"""Tests for MAKE Autonomous Agent Core V2 — Revision Engine."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.revision_engine import RevisionEngine, RevisionStrategy
from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType


class TestRevisionEngine:
    def test_create_revision(self):
        engine = RevisionEngine()
        parent_id = uuid4()
        new_id = uuid4()
        revision = engine.create_revision(
            parent_execution_id=parent_id,
            new_execution_id=new_id,
            strategy=RevisionStrategy.RETRY_TOOL,
            reason="Tool failed due to timeout",
            evidence={"timeout": 30},
        )
        assert revision.revision_id is not None
        assert revision.parent_execution_id == parent_id
        assert revision.new_execution_id == new_id
        assert revision.strategy == RevisionStrategy.RETRY_TOOL
        assert revision.reason == "Tool failed due to timeout"

    def test_get_revisions(self):
        engine = RevisionEngine()
        parent_id = uuid4()
        engine.create_revision(parent_id, uuid4(), RevisionStrategy.MODIFY_PARAMETERS, "r1", {})
        engine.create_revision(parent_id, uuid4(), RevisionStrategy.RETRY_TOOL, "r2", {})
        revisions = engine.get_revisions(parent_id)
        assert len(revisions) == 2

    def test_apply_revision_preserves_completed(self):
        engine = RevisionEngine()
        graph = ExecutionGraph.create()
        node1 = ExecutionNode.create(NodeType.INTENT, graph.execution_id)
        graph.add_node(node1)
        node2 = ExecutionNode.create(NodeType.TASK, graph.execution_id, dependency_ids=[node1.node_id])
        graph.add_node(node2)
        graph.update_node_state(node1.node_id, ExecutionState.COMPLETED)
        graph.update_node_state(node2.node_id, ExecutionState.FAILED)
        revision = engine.create_revision(
            graph.execution_id,
            uuid4(),
            RevisionStrategy.RETRY_TOOL,
            "retry failed task",
            {},
            preserved_components=[node1.node_id],
        )
        new_graph = engine.apply_revision_to_graph(graph, revision)
        assert new_graph.execution_id == revision.new_execution_id
        assert node1.node_id in new_graph.nodes
        assert node2.node_id not in new_graph.nodes

    def test_revision_to_dict(self):
        engine = RevisionEngine()
        parent_id = uuid4()
        new_id = uuid4()
        revision = engine.create_revision(
            parent_execution_id=parent_id,
            new_execution_id=new_id,
            strategy=RevisionStrategy.ALTERNATE_TOOL,
            reason="Primary tool unavailable",
            evidence={"tool": "video_gen"},
            changed_constraints={"model": "backup"},
            changed_plan={"steps": 3},
        )
        data = revision.to_dict()
        assert data["parent_execution_id"] == str(parent_id)
        assert data["new_execution_id"] == str(new_id)
        assert data["strategy"] == "alternate_tool"
        assert data["changed_constraints"] == {"model": "backup"}
