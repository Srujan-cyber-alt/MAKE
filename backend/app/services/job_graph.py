import uuid
from typing import Optional, Dict, Any, List
from app.schemas.phase7 import JobGraph, JobGraphNode
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class JobGraphEngine:
    @staticmethod
    def create_graph(transformation_id: str, nodes: List[Dict[str, Any]]) -> JobGraph:
        graph = JobGraph(
            graph_id=str(uuid.uuid4()),
            transformation_id=transformation_id,
            nodes=[JobGraphNode(**node) for node in nodes],
            edges=JobGraphEngine._build_edges(nodes),
            status="pending",
        )
        return graph

    @staticmethod
    def _build_edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        edges = []
        for i, node in enumerate(nodes):
            if i > 0:
                edges.append({"from": nodes[i - 1]["node_id"], "to": node["node_id"]})
        return edges

    @staticmethod
    async def update_node(graph: JobGraph, node_id: str, **updates) -> JobGraph:
        for node in graph.nodes:
            if node.node_id == node_id:
                for key, value in updates.items():
                    if hasattr(node, key):
                        setattr(node, key, value)
                break
        if redis_service.is_connected():
            await redis_service.set_json(f"job_graph:{graph.graph_id}", graph.model_dump(), ex=86400)
        return graph

    @staticmethod
    async def mark_node_completed(graph: JobGraph, node_id: str, output: Dict[str, Any]) -> JobGraph:
        return await JobGraphEngine.update_node(
            graph,
            node_id,
            status="completed",
            progress=1.0,
            output=output,
        )

    @staticmethod
    async def mark_node_failed(graph: JobGraph, node_id: str, error: str) -> JobGraph:
        return await JobGraphEngine.update_node(
            graph,
            node_id,
            status="failed",
            error=error,
        )

    @staticmethod
    def get_next_pending_node(graph: JobGraph) -> Optional[JobGraphNode]:
        pending_nodes = [n for n in graph.nodes if n.status == "pending"]
        if not pending_nodes:
            return None
        ready = []
        for node in pending_nodes:
            deps_met = all(
                any(n.node_id == dep and n.status == "completed" for n in graph.nodes)
                for dep in node.dependencies
            )
            if deps_met:
                ready.append(node)
        return ready[0] if ready else None

    @staticmethod
    def is_complete(graph: JobGraph) -> bool:
        return all(node.status in ("completed", "failed", "cancelled") for node in graph.nodes)

    @staticmethod
    def has_failure(graph: JobGraph) -> bool:
        return any(node.status == "failed" for node in graph.nodes)
