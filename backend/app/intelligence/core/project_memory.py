"""
MAKE Autonomous Agent Core V2 — Project Memory.

Persistent project-level memory with versioning and provenance.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime


class EntityType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    OBJECT = "object"
    MATERIAL = "material"
    LIGHTING = "lighting"
    CAMERA = "camera"
    STYLE = "style"
    RULE = "rule"
    TIMELINE = "timeline"
    RELATIONSHIP = "relationship"
    REFERENCE = "reference"


class MemoryAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"


@dataclass
class ProjectEntity:
    entity_id: UUID
    entity_type: EntityType
    name: str
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": str(self.entity_id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class ProjectVersion:
    version_id: UUID
    project_id: UUID
    state_snapshot: Dict[str, Any]
    action: MemoryAction
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": str(self.version_id),
            "project_id": str(self.project_id),
            "state_snapshot": self.state_snapshot,
            "action": self.action.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ProjectState:
    project_id: UUID
    entities: Dict[str, ProjectEntity]
    versions: List[ProjectVersion]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "versions": [v.to_dict() for v in self.versions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class ProjectMemory:
    def __init__(self) -> None:
        self._states: Dict[UUID, ProjectState] = {}

    def create_project(self, project_id: UUID, metadata: Optional[Dict[str, Any]] = None) -> ProjectState:
        now = datetime.utcnow()
        state = ProjectState(
            project_id=project_id,
            entities={},
            versions=[],
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self._states[project_id] = state
        self._record_version(state, MemoryAction.CREATE)
        return state

    def get_project(self, project_id: UUID) -> Optional[ProjectState]:
        return self._states.get(project_id)

    def add_entity(self, project_id: UUID, entity: ProjectEntity) -> None:
        state = self._states.get(project_id)
        if not state:
            raise KeyError(f"Project {project_id} not found")
        state.entities[str(entity.entity_id)] = entity
        state.updated_at = datetime.utcnow()
        self._record_version(state, MemoryAction.CREATE)

    def update_entity(self, project_id: UUID, entity_id: UUID, properties: Dict[str, Any]) -> Optional[ProjectEntity]:
        state = self._states.get(project_id)
        if not state:
            return None
        entity = state.entities.get(str(entity_id))
        if not entity:
            return None
        entity.properties.update(properties)
        entity.version += 1
        entity.updated_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()
        self._record_version(state, MemoryAction.UPDATE)
        return entity

    def get_entity(self, project_id: UUID, entity_id: UUID) -> Optional[ProjectEntity]:
        state = self._states.get(project_id)
        if not state:
            return None
        return state.entities.get(str(entity_id))

    def list_entities(self, project_id: UUID, entity_type: Optional[EntityType] = None) -> List[ProjectEntity]:
        state = self._states.get(project_id)
        if not state:
            return []
        entities = list(state.entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        return entities

    def rollback(self, project_id: UUID, version_id: UUID) -> Optional[ProjectState]:
        state = self._states.get(project_id)
        if not state:
            return None
        target_version = None
        for v in state.versions:
            if v.version_id == version_id:
                target_version = v
                break
        if not target_version:
            return None
        snapshot = target_version.state_snapshot
        state.entities = {
            k: ProjectEntity(
                entity_id=UUID(k),
                entity_type=EntityType(v["entity_type"]),
                name=v["name"],
                properties=v["properties"],
                created_at=datetime.fromisoformat(v["created_at"]),
                updated_at=datetime.fromisoformat(v["updated_at"]),
                version=v["version"],
                metadata=v.get("metadata", {}),
            )
            for k, v in snapshot.get("entities", {}).items()
        }
        state.updated_at = datetime.utcnow()
        self._record_version(state, MemoryAction.ROLLBACK)
        return state

    def get_versions(self, project_id: UUID) -> List[ProjectVersion]:
        state = self._states.get(project_id)
        if not state:
            return []
        return list(state.versions)

    def _record_version(self, state: ProjectState, action: MemoryAction) -> None:
        version = ProjectVersion(
            version_id=uuid4(),
            project_id=state.project_id,
            state_snapshot=state.to_dict(),
            action=action,
            created_at=datetime.utcnow(),
        )
        state.versions.append(version)
