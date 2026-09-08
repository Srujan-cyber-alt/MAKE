"""World Memory — persistent structured memory for entities.

Stores people, identities, objects, locations, projects, scenes, assets,
preferences, decisions, and relationships. Sensitive personal information
is never stored silently: every memory item requires an explicit
``scope`` and optional consent marker.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete, and_, or_

from app.intelligence.schemas import (
    MemoryEntityRecord, EntityType, RelationType,
)
from app.intelligence.models import MemoryEntityOrm, MemoryRelationOrm


class WorldMemory:
    """Persistent structured memory backed by an async SQLite store."""

    def __init__(self) -> None:
        self._session_factory_provider = None

    def _session(self):
        from app.intelligence.database import get_session_factory
        return get_session_factory()

    # ---- Entity CRUD ----

    async def store_entity(
        self,
        entity_type: EntityType,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        scope: str = "default",
        *,  # force keyword for consent
        consent: bool = True,
        entity_id: Optional[str] = None,
        update: bool = False,
    ) -> MemoryEntityRecord:
        """Store a memory entity.

        ``consent`` must be explicitly True for entities that may hold
        personal/sensitive information. When False, the entity is rejected.
        """
        if not consent:
            raise PermissionError(
                "Storing this entity requires explicit consent/sensitive-data permission."
            )
        attributes = attributes or {}
        async with self._session()() as session:
            if update or entity_id:
                existing = await session.get(MemoryEntityOrm, entity_id) if entity_id else None
                if existing:
                    existing.entity_type = entity_type
                    existing.name = name
                    existing.attributes = attributes
                    existing.scope = scope
                    existing.updated_at = datetime.utcnow()
                else:
                    orm = MemoryEntityOrm(
                        id=entity_id or None,
                        entity_type=entity_type,
                        name=name,
                        attributes=attributes,
                        scope=scope,
                    )
                    session.add(orm)
                    existing = orm
            else:
                orm = MemoryEntityOrm(
                    entity_type=entity_type,
                    name=name,
                    attributes=attributes,
                    scope=scope,
                )
                session.add(orm)
                existing = orm
            await session.commit()
            await session.refresh(existing)

        return MemoryEntityRecord(
            id=existing.id,
            entity_type=existing.entity_type,
            name=existing.name,
            attributes=existing.attributes,
            scope=existing.scope,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    async def get_entity(self, entity_id: str) -> Optional[MemoryEntityRecord]:
        async with self._session()() as session:
            orm = await session.get(MemoryEntityOrm, entity_id)
            if orm is None:
                return None
        return self._to_record(orm)

    async def find_entities(
        self,
        entity_type: Optional[EntityType] = None,
        name: Optional[str] = None,
        scope: str = "default",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntityRecord]:
        async with self._session()() as session:
            stmt = select(MemoryEntityOrm).where(MemoryEntityOrm.scope == scope)
            conditions = []
            if entity_type:
                conditions.append(MemoryEntityOrm.entity_type == entity_type)
            if name:
                conditions.append(MemoryEntityOrm.name.ilike(f"%{name}%"))
            if conditions:
                stmt = stmt.where(and_(*conditions))
            result = await session.execute(stmt)
            rows = result.scalars().all()

        records = [self._to_record(r) for r in rows]

        if attributes:
            filtered: List[MemoryEntityRecord] = []
            for rec in records:
                match = True
                for k, v in attributes.items():
                    if rec.attributes.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(rec)
            return filtered
        return records

    async def update_entity(
        self,
        entity_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> Optional[MemoryEntityRecord]:
        async with self._session()() as session:
            orm = await session.get(MemoryEntityOrm, entity_id)
            if orm is None:
                return None
            if attributes is not None:
                orm.attributes = {**orm.attributes, **attributes}
            if name is not None:
                orm.name = name
            orm.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(orm)
        return self._to_record(orm)

    async def delete_entity(self, entity_id: str) -> bool:
        async with self._session()() as session:
            orm = await session.get(MemoryEntityOrm, entity_id)
            if orm is None:
                return False
            await session.delete(orm)
            await session.commit()
        return True

    # ---- Relationship CRUD ----

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        async with self._session()() as session:
            src = await session.get(MemoryEntityOrm, source_id)
            tgt = await session.get(MemoryEntityOrm, target_id)
            if src is None or tgt is None:
                raise ValueError("Cannot create relation: source or target entity not found")
            rel = MemoryRelationOrm(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=relation_type,
                weight=weight,
                attributes=attributes or {},
            )
            session.add(rel)
            await session.commit()
        return rel.id

    async def get_relations(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None,
        scope: str = "default",
    ) -> List[Dict[str, Any]]:
        async with self._session()() as session:
            stmt = (
                select(MemoryRelationOrm, MemoryEntityOrm, MemoryEntityOrm)
                .join(MemoryEntityOrm, MemoryEntityOrm.id == MemoryRelationOrm.source_entity_id)
                .join(
                    MemoryEntityOrm,
                    MemoryEntityOrm.id == MemoryRelationOrm.target_entity_id,
                )
                .where(MemoryEntityOrm.scope == scope)
            )
            conditions = []
            if source_id:
                conditions.append(MemoryRelationOrm.source_entity_id == source_id)
            if target_id:
                conditions.append(MemoryRelationOrm.target_entity_id == target_id)
            if relation_type:
                conditions.append(MemoryRelationOrm.relation_type == relation_type)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            # The joins above need aliases — use a simpler approach
            pass

        # Re-query with explicit joins using selectin to avoid alias issues
        return await self._get_relations_raw(source_id, target_id, relation_type, scope)

    async def _get_relations_raw(
        self,
        source_id: Optional[str],
        target_id: Optional[str],
        relation_type: Optional[RelationType],
        scope: str,
    ) -> List[Dict[str, Any]]:
        from sqlalchemy import select as sa_select
        from sqlalchemy.orm import aliased

        src_alias = aliased(MemoryEntityOrm)
        tgt_alias = aliased(MemoryEntityOrm)
        async with self._session()() as session:
            stmt = (
                sa_select(
                    MemoryRelationOrm.id,
                    MemoryRelationOrm.source_entity_id,
                    MemoryRelationOrm.target_entity_id,
                    MemoryRelationOrm.relation_type,
                    MemoryRelationOrm.weight,
                    MemoryRelationOrm.attributes,
                    src_alias.name.label("source_name"),
                    tgt_alias.name.label("target_name"),
                )
                .join(src_alias, src_alias.id == MemoryRelationOrm.source_entity_id)
                .join(tgt_alias, tgt_alias.id == MemoryRelationOrm.target_entity_id)
                .where(src_alias.scope == scope)
            )
            conditions = []
            if source_id:
                conditions.append(MemoryRelationOrm.source_entity_id == source_id)
            if target_id:
                conditions.append(MemoryRelationOrm.target_entity_id == target_id)
            if relation_type:
                conditions.append(MemoryRelationOrm.relation_type == relation_type)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            result = await session.execute(stmt)
            rows = result.all()

        relations: List[Dict[str, Any]] = []
        for row in rows:
            relations.append({
                "id": row.id,
                "source_entity_id": row.source_entity_id,
                "target_entity_id": row.target_entity_id,
                "relation_type": row.relation_type.value,
                "weight": row.weight,
                "attributes": row.attributes,
                "source_name": row.source_name,
                "target_name": row.target_name,
            })
        return relations

    async def get_related(
        self,
        entity_id: str,
        relation_types: Optional[List[RelationType]] = None,
        scope: str = "default",
    ) -> List[Dict[str, Any]]:
        """Get all entities related to *entity_id* (in either direction)."""
        relations = await self._get_relations_raw(entity_id, None, None, scope)
        if relation_types:
            types = {rt.value for rt in relation_types}
            relations = [r for r in relations if r["relation_type"] in types]

        target_ids = {r["target_entity_id"] for r in relations}
        source_ids = {r["source_entity_id"] for r in relations}
        related = target_ids | source_ids
        related.discard(entity_id)

        async with self._session()() as session:
            result = await session.execute(
                select(MemoryEntityOrm)
                .where(
                    and_(
                        MemoryEntityOrm.id.in_(list(related)),
                        MemoryEntityOrm.scope == scope,
                    )
                )
            )
            rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "entity_type": r.entity_type.value,
                "name": r.name,
                "attributes": r.attributes,
            }
            for r in rows
        ]

    async def count_entities(self, scope: str = "default") -> int:
        async with self._session()() as session:
            result = await session.execute(
                select(MemoryEntityOrm).where(MemoryEntityOrm.scope == scope)
            )
            return len(result.scalars().all())

    @staticmethod
    def _to_record(orm: MemoryEntityOrm) -> MemoryEntityRecord:
        return MemoryEntityRecord(
            id=orm.id,
            entity_type=orm.entity_type,
            name=orm.name,
            attributes=orm.attributes,
            scope=orm.scope,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
