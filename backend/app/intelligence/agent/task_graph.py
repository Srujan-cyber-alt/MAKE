from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum


class GraphStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GraphNode:
    task_id: str
    name: str
    status: GraphStatus = GraphStatus.READY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}
        self._reverse_adjacency: Dict[str, List[str]] = {}

    def add_node(self, task_id: str, name: str) -> GraphNode:
        node = GraphNode(task_id=task_id, name=name)
        self._nodes[task_id] = node
        self._adjacency.setdefault(task_id, [])
        self._reverse_adjacency.setdefault(task_id, [])
        return node

    def add_edge(self, source: str, target: str) -> None:
        if source not in self._nodes or target not in self._nodes:
            raise ValueError("Source and target nodes must exist")
        edge = GraphEdge(source=source, target=target)
        self._edges.append(edge)
        self._adjacency[source].append(target)
        self._reverse_adjacency[target].append(source)

    def get_node(self, task_id: str) -> Optional[GraphNode]:
        return self._nodes.get(task_id)

    def get_edges(self, task_id: str) -> List[GraphEdge]:
        return [e for e in self._edges if e.source == task_id]

    def get_dependencies(self, task_id: str) -> List[str]:
        return self._reverse_adjacency.get(task_id, [])

    def get_dependents(self, task_id: str) -> List[str]:
        return self._adjacency.get(task_id, [])

    def topological_sort(self) -> List[str]:
        in_degree = {tid: 0 for tid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        queue.sort()
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in sorted(self._adjacency.get(node, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort()
        return result

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def get_parallel_batches(self) -> List[List[str]]:
        batches = []
        remaining = set(self._nodes.keys())
        while remaining:
            batch = []
            for node in sorted(remaining):
                deps = self._reverse_adjacency.get(node, [])
                if all(d not in remaining for d in deps):
                    batch.append(node)
            if not batch:
                break
            batches.append(batch)
            for node in batch:
                remaining.discard(node)
        return batches

    def get_critical_path(self) -> List[str]:
        try:
            order = self.topological_sort()
            return order if order else list(self._nodes.keys())
        except Exception:
            return list(self._nodes.keys())

    def remove_node(self, task_id: str) -> None:
        if task_id in self._nodes:
            del self._nodes[task_id]
            self._edges = [e for e in self._edges if e.source != task_id and e.target != task_id]
            self._adjacency.pop(task_id, None)
            self._reverse_adjacency.pop(task_id, None)
            for adj in self._adjacency.values():
                while task_id in adj:
                    adj.remove(task_id)
            for radj in self._reverse_adjacency.values():
                while task_id in radj:
                    radj.remove(task_id)

    def get_ready_tasks(self) -> List[str]:
        ready = []
        for task_id in self._nodes:
            deps = self._reverse_adjacency.get(task_id, [])
            if all(d not in self._nodes for d in deps):
                ready.append(task_id)
        return ready
