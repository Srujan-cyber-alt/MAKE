"""
MAKE Autonomous Agent Core V2 — World Continuity.

Extends RealityGraph and WorldMemory for persistent world continuity.
Resolves entities from project memory.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from app.intelligence.core.project_memory import ProjectMemory, ProjectEntity, EntityType


class EntityResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"


@dataclass
class EntityReference:
    reference_id: UUID
    entity_type: EntityType
    name: str
    properties: Dict[str, Any]
    resolution_status: EntityResolutionStatus
    resolved_entity_id: Optional[UUID]
    confidence: float
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": str(self.reference_id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "properties": self.properties,
            "resolution_status": self.resolution_status.value,
            "resolved_entity_id": str(self.resolved_entity_id) if self.resolved_entity_id else None,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WorldContinuityState:
    project_id: UUID
    entity_registry: Dict[str, EntityReference]
    relationship_graph: Dict[str, List[str]]
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "entity_registry": {k: v.to_dict() for k, v in self.entity_registry.items()},
            "relationship_graph": self.relationship_graph,
            "last_updated": self.last_updated.isoformat(),
        }


class WorldContinuity:
    def __init__(self, project_memory: ProjectMemory) -> None:
        self.project_memory = project_memory
        self._world_states: Dict[UUID, WorldContinuityState] = {}

    def register_entity(self, project_id: UUID, reference: EntityReference) -> None:
        state = self._get_or_create_state(project_id)
        key = f"{reference.entity_type.value}:{reference.name}"
        state.entity_registry[key] = reference
        state.last_updated = datetime.utcnow()

    def resolve_entity(self, project_id: UUID, entity_type: EntityType, name: str) -> Optional[EntityReference]:
        state = self._world_states.get(project_id)
        if not state:
            return None
        key = f"{entity_type.value}:{name}"
        ref = state.entity_registry.get(key)
        if ref and ref.resolution_status == EntityResolutionStatus.RESOLVED:
            return ref
        return None

    def get_entity_from_memory(self, project_id: UUID, entity_id: UUID) -> Optional[ProjectEntity]:
        return self.project_memory.get_entity(project_id, entity_id)

    def add_relationship(self, project_id: UUID, entity_a: str, entity_b: str) -> None:
        state = self._get_or_create_state(project_id)
        state.relationship_graph.setdefault(entity_a, []).append(entity_b)
        state.relationship_graph.setdefault(entity_b, []).append(entity_a)
        state.last_updated = datetime.utcnow()

    def get_world_state(self, project_id: UUID) -> Optional[WorldContinuityState]:
        return self._world_states.get(project_id)

    def _get_or_create_state(self, project_id: UUID) -> WorldContinuityState:
        if project_id not in self._world_states:
            self._world_states[project_id] = WorldContinuityState(
                project_id=project_id,
                entity_registry={},
                relationship_graph={},
                last_updated=datetime.utcnow(),
            )
        return self._world_states[project_id]


class EntityResolver:
    def __init__(self, world_continuity: WorldContinuity) -> None:
        self.world_continuity = world_continuity

    def resolve(self, project_id: UUID, entity_type: EntityType, name: str, properties: Optional[Dict[str, Any]] = None) -> EntityReference:
        existing = self.world_continuity.resolve_entity(project_id, entity_type, name)
        if existing:
            return existing
        # Try to find in project memory
        entities = self.world_continuity.project_memory.list_entities(project_id, entity_type)
        for entity in entities:
            if entity.name.lower() == name.lower():
                ref = EntityReference(
                    reference_id=UUID(int=0),
                    entity_type=entity_type,
                    name=name,
                    properties=properties or entity.properties,
                    resolution_status=EntityResolutionStatus.RESOLVED,
                    resolved_entity_id=entity.entity_id,
                    confidence=1.0,
                    created_at=datetime.utcnow(),
                )
                import hashlib
                content = f"{project_id}:{entity_type}:{name}:{entity.entity_id}"
                ref.reference_id = UUID(hashlib.sha256(content.encode()).hexdigest()[:32])
                self.world_continuity.register_entity(project_id, ref)
                return ref
        # Entity not found - report missing
        ref = EntityReference(
            reference_id=UUID(int=0),
            entity_type=entity_type,
            name=name,
            properties=properties or {},
            resolution_status=EntityResolutionStatus.MISSING,
            resolved_entity_id=None,
            confidence=0.0,
            created_at=datetime.utcnow(),
        )
        import hashlib
        content = f"{project_id}:{entity_type}:{name}:missing"
        ref.reference_id = UUID(hashlib.sha256(content.encode()).hexdigest()[:32])
        self.world_continuity.register_entity(project_id, ref)
        return ref
