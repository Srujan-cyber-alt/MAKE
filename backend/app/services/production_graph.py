"""
Production Graph for MAKE AI Video Phase 18.

Tracks dependencies between production elements:
Scene → Shot → Generation → Edit → VFX → Audio → Color → QC → Export
"""

from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class NodeType:
    BRIEF = "brief"
    STORY = "story"
    SCENE = "scene"
    SHOT = "shot"
    CHARACTER = "character"
    WORLD = "world"
    PRODUCT = "product"
    GENERATION = "generation"
    EDIT = "edit"
    VFX = "vfx"
    AUDIO = "audio"
    COLOR = "color"
    GRAPHICS = "graphics"
    QC = "qc"
    MASTER = "master"
    EXPORT = "export"


class NodeStatus:
    PENDING = "pending"
    READY = "ready"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProductionGraph:
    @staticmethod
    def create_graph(production_id: str) -> Dict[str, Any]:
        return {
            "graph_id": str(uuid.uuid4()),
            "production_id": production_id,
            "nodes": {},
            "edges": [],
            "status": "initialized",
        }

    @staticmethod
    def add_node(graph: Dict[str, Any], node_type: str, node_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        node = {
            "node_id": node_id,
            "type": node_type,
            "status": NodeStatus.PENDING,
            "data": data or {},
            "dependencies": [],
            "dependents": [],
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        graph["nodes"][node_id] = node
        return node

    @staticmethod
    def add_edge(graph: Dict[str, Any], from_node_id: str, to_node_id: str, edge_type: str = "depends_on") -> Dict[str, Any]:
        edge = {
            "edge_id": str(uuid.uuid4()),
            "from": from_node_id,
            "to": to_node_id,
            "type": edge_type,
        }
        graph["edges"].append(edge)
        if from_node_id in graph["nodes"]:
            graph["nodes"][from_node_id]["dependents"].append(to_node_id)
        if to_node_id in graph["nodes"]:
            graph["nodes"][to_node_id]["dependencies"].append(from_node_id)
        return edge

    @staticmethod
    def update_node_status(graph: Dict[str, Any], node_id: str, status: str) -> bool:
        node = graph.get("nodes", {}).get(node_id)
        if not node:
            return False
        node["status"] = status
        node["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        if status == NodeStatus.COMPLETED:
            ProductionGraph._propagate_completion(graph, node_id)
        elif status == NodeStatus.FAILED:
            ProductionGraph._propagate_failure(graph, node_id)
        return True

    @staticmethod
    def _propagate_completion(graph: Dict[str, Any], node_id: str):
        for edge in graph.get("edges", []):
            if edge["from"] == node_id:
                to_node = graph.get("nodes", {}).get(edge["to"])
                if to_node and to_node["status"] == NodeStatus.PENDING:
                    deps_met = all(
                        graph.get("nodes", {}).get(dep, {}).get("status") == NodeStatus.COMPLETED
                        for dep in to_node.get("dependencies", [])
                    )
                    if deps_met:
                        to_node["status"] = NodeStatus.READY

    @staticmethod
    def _propagate_failure(graph: Dict[str, Any], node_id: str):
        for edge in graph.get("edges", []):
            if edge["from"] == node_id:
                to_node = graph.get("nodes", {}).get(edge["to"])
                if to_node and to_node["status"] in (NodeStatus.PENDING, NodeStatus.READY):
                    to_node["status"] = NodeStatus.BLOCKED

    @staticmethod
    def get_ready_nodes(graph: Dict[str, Any]) -> List[str]:
        return [
            nid for nid, node in graph.get("nodes", {}).items()
            if node.get("status") == NodeStatus.READY
        ]

    @staticmethod
    def get_blocked_nodes(graph: Dict[str, Any]) -> List[str]:
        return [
            nid for nid, node in graph.get("nodes", {}).items()
            if node.get("status") == NodeStatus.BLOCKED
        ]

    @staticmethod
    def get_production_status(graph: Dict[str, Any]) -> Dict[str, Any]:
        nodes = graph.get("nodes", {})
        total = len(nodes)
        completed = sum(1 for n in nodes.values() if n.get("status") == NodeStatus.COMPLETED)
        failed = sum(1 for n in nodes.values() if n.get("status") == NodeStatus.FAILED)
        blocked = sum(1 for n in nodes.values() if n.get("status") == NodeStatus.BLOCKED)
        ready = sum(1 for n in nodes.values() if n.get("status") == NodeStatus.READY)
        in_progress = sum(1 for n in nodes.values() if n.get("status") == NodeStatus.IN_PROGRESS)
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "ready": ready,
            "in_progress": in_progress,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }


production_graph = ProductionGraph()
