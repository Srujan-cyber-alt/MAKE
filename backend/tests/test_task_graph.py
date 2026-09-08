"""Tests for the Task Graph module."""

import pytest
from app.intelligence.agent.task_graph import TaskGraph, GraphNode, GraphEdge, GraphStatus


class TestTaskGraph:
    def test_create_empty_graph(self):
        graph = TaskGraph()
        assert graph is not None

    def test_add_node(self):
        graph = TaskGraph()
        node = graph.add_node("task_1", "Test Task")
        assert node is not None
        assert node.task_id == "task_1"
        assert node.name == "Test Task"

    def test_add_edge(self):
        graph = TaskGraph()
        graph.add_node("task_1", "Task 1")
        graph.add_node("task_2", "Task 2")
        graph.add_edge("task_1", "task_2")
        edges = graph.get_edges("task_1")
        assert len(edges) == 1
        assert edges[0].target == "task_2"

    def test_topological_sort_linear(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        order = graph.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_topological_sort_parallel(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        order = graph.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")

    def test_detect_cycle(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", "a")
        assert graph.has_cycle() is True

    def test_no_cycle(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        assert graph.has_cycle() is False

    def test_get_parallel_batches(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        batches = graph.get_parallel_batches()
        assert len(batches) >= 2
        assert "a" in batches[0]

    def test_get_critical_path(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_node("c", "C")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        path = graph.get_critical_path()
        assert "a" in path
        assert "b" in path
        assert "c" in path

    def test_remove_node(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_edge("a", "b")
        graph.remove_node("a")
        assert graph.get_node("a") is None

    def test_get_ready_tasks(self):
        graph = TaskGraph()
        graph.add_node("a", "A")
        graph.add_node("b", "B")
        graph.add_edge("a", "b")
        ready = graph.get_ready_tasks()
        assert "a" in ready
        assert "b" not in ready
