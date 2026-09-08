"""Reality Graph — entity/relationship graph for MAKE Intelligence Core.

Represents relationships like:
    Person → owns → Object
    Person → located_at → Place
    Object → belongs_to → Project
    Scene → contains → Object
    Scene → contains → Person
    Job → produced → Asset

Supports arbitrary extensible relationship types.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Set

from sqlalchemy import select, delete, and_
from sqlalchemy.orm import aliased

from app.intelligence.schemas import (
    GraphNodeRecord, GraphEdgeRecord, EntityType, RelationType,
)
from app.intelligence.models import GraphNodeOrm, GraphEdgeOrm


class RealityGraph:
    """Property graph stored in SQLite with indexable nodes and edges."""

    def __init__(self) -> None:
        pass

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    # ---- Nodes ----

    async def add_node(
        self,
        name: str,
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> GraphNodeRecord:
        async with self._session()() as session:
            if node_id:
                existing = await session.get(GraphNodeOrm, node_id)
                if existing:
                    existing.name = name
                    existing.entity_type = entity_type
                    existing.attributes = attributes or {}
                    await session.commit()
                    await session.refresh(existing)
                    return self._node_to_record(existing)
            orm = GraphNodeOrm(
                id=node_id,
                name=name,
                entity_type=entity_type,
                attributes=attributes or {},
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._node_to_record(orm)

    async def get_node(self, node_id: str) -> Optional[GraphNodeRecord]:
        async with self._session()() as session:
            orm = await session.get(GraphNodeOrm, node_id)
            if orm is None:
                return None
        return self._node_to_record(orm)

    async def find_nodes(
        self,
        name: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> List[GraphNodeRecord]:
        async with self._session()() as session:
            stmt = select(GraphNodeOrm)
            conditions = []
            if name:
                conditions.append(GraphNodeOrm.name.ilike(f"%{name}%"))
            if entity_type:
                conditions.append(GraphNodeOrm.entity_type == entity_type)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._node_to_record(r) for r in rows]

    async def delete_node(self, node_id: str) -> bool:
        async with self._session()() as session:
            orm = await session.get(GraphNodeOrm, node_id)
            if orm is None:
                return False
            await session.delete(orm)
            await session.commit()
        return True

    # ---- Edges ----

    async def add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation_type: str,
        weight: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> GraphEdgeRecord:
        async with self._session()() as session:
            src = await session.get(GraphNodeOrm, source_node_id)
            tgt = await session.get(GraphNodeOrm, target_node_id)
            if src is None:
                raise ValueError(f"Source node {source_node_id} not found")
            if tgt is None:
                raise ValueError(f"Target node {target_node_id} not found")
            if edge_id:
                existing = await session.get(GraphEdgeOrm, edge_id)
                if existing:
                    existing.source_node_id = source_node_id
                    existing.target_node_id = target_node_id
                    existing.relation_type = relation_type
                    existing.weight = weight
                    existing.attributes = attributes or {}
                    await session.commit()
                    await session.refresh(existing)
                    return self._edge_to_record(existing)
            orm = GraphEdgeOrm(
                id=edge_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                relation_type=relation_type,
                weight=weight,
                attributes=attributes or {},
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._edge_to_record(orm)

    async def get_edges(
        self,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> List[GraphEdgeRecord]:
        async with self._session()() as session:
            stmt = select(GraphEdgeOrm)
            conditions = []
            if source_node_id:
                conditions.append(GraphEdgeOrm.source_node_id == source_node_id)
            if target_node_id:
                conditions.append(GraphEdgeOrm.target_node_id == target_node_id)
            if relation_type:
                conditions.append(GraphEdgeOrm.relation_type == relation_type)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._edge_to_record(r) for r in rows]

    async def get_neighbors(
        self,
        node_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",
    ) -> List[GraphNodeRecord]:
        """Get neighboring nodes.

        direction: 'out' (edges from node), 'in' (edges to node), 'both'.
        """
        node_alias = aliased(GraphNodeOrm)
        async with self._session()() as session:
            stmt = select(GraphNodeOrm).join(
                GraphEdgeOrm,
                GraphEdgeOrm.source_node_id == GraphNodeOrm.id,
                isouter=True,
            )
            # We need two queries for in/out edges
            target_ids: Set[str] = set()

            # Out edges: node → ?
            stmt_out = select(GraphEdgeOrm.target_node_id).where(
                GraphEdgeOrm.source_node_id == node_id
            )
            # In edges: ? → node
            stmt_in = select(GraphEdgeOrm.source_node_id).where(
                GraphEdgeOrm.target_node_id == node_id
            )

            if direction in ("out", "both"):
                result = await session.execute(stmt_out)
                target_ids.update(r[0] for r in result)
            if direction in ("in", "both"):
                result = await session.execute(stmt_in)
                target_ids.update(r[0] for r in result)

            target_ids.discard(node_id)

            if not target_ids:
                return []

            q = select(GraphNodeOrm).where(GraphNodeOrm.id.in_(list(target_ids)))
            result = await session.execute(q)
            rows = result.scalars().all()

        return [self._node_to_record(r) for r in rows]

    async def traverse(
        self,
        start_node_id: str,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """BFS traversal returning path information."""
        visited: Set[str] = {start_node_id}
        current_level: Set[str] = {start_node_id}
        results: List[Dict[str, Any]] = []

        for depth in range(max_depth):
            next_level: Set[str] = set()
            for nid in current_level:
                edges = await self.get_edges(source_node_id=nid)
                if relation_types:
                    edges = [e for e in edges if e.relation_type in relation_types]
                for edge in edges:
                    if edge.target_node_id not in visited:
                        visited.add(edge.target_node_id)
                        next_level.add(edge.target_node_id)
                        node = await self.get_node(edge.target_node_id)
                        results.append({
                            "depth": depth + 1,
                            "source_id": nid,
                            "target_id": edge.target_node_id,
                            "relation_type": edge.relation_type,
                            "target_node": node.model_dump() if node else None,
                        })
            current_level = next_level
            if not current_level:
                break

        return results

    async def path_exists(
        self,
        source_node_id: str,
        target_node_id: str,
        relation_type: Optional[str] = None,
        max_depth: int = 5,
    ) -> bool:
        if source_node_id == target_node_id:
            return True
        visited: Set[str] = {source_node_id}
        current = {source_node_id}
        for _ in range(max_depth):
            neighbors = await self.get_neighbors(
                current.pop() if len(current) == 1 else next(iter(current)),
                relation_types=[relation_type] if relation_type else None,
            )
            for n in neighbors:
                if n.id == target_node_id:
                    return True
                if n.id not in visited:
                    visited.add(n.id)
                    current.add(n.id)
        return False

    async def clear_all(self) -> int:
        async with self._session()() as session:
            r1 = await session.execute(delete(GraphEdgeOrm))
            r2 = await session.execute(delete(GraphNodeOrm))
            await session.commit()
            return r1.rowcount + r2.rowcount

    @staticmethod
    def _node_to_record(orm: GraphNodeOrm) -> GraphNodeRecord:
        return GraphNodeRecord(
            id=orm.id,
            name=orm.name,
            entity_type=orm.entity_type,
            attributes=orm.attributes,
        )

    @staticmethod
    def _edge_to_record(orm: GraphEdgeOrm) -> GraphEdgeRecord:
        return GraphEdgeRecord(
            id=orm.id,
            source_node_id=orm.source_node_id,
            target_node_id=orm.target_node_id,
            relation_type=orm.relation_type,
            weight=orm.weight,
            attributes=orm.attributes,
        )
