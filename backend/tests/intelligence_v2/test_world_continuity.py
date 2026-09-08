"""Tests for MAKE Autonomous Agent Core V2 — World Continuity."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.world_continuity import WorldContinuity, EntityResolver, EntityResolutionStatus
from app.intelligence.core.project_memory import ProjectMemory, ProjectEntity, EntityType


class TestWorldContinuity:
    def test_register_and_resolve_entity(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        entity = ProjectEntity(
            entity_id=uuid4(),
            entity_type=EntityType.CHARACTER,
            name="Alice",
            properties={"hair": "blonde"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        memory.add_entity(project_id, entity)

        continuity = WorldContinuity(memory)
        resolver = EntityResolver(continuity)
        ref = resolver.resolve(project_id, EntityType.CHARACTER, "Alice")
        assert ref.resolution_status == EntityResolutionStatus.RESOLVED
        assert ref.resolved_entity_id == entity.entity_id
        assert ref.confidence == 1.0

    def test_resolve_missing_entity(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        continuity = WorldContinuity(memory)
        resolver = EntityResolver(continuity)
        ref = resolver.resolve(project_id, EntityType.CHARACTER, "Unknown")
        assert ref.resolution_status == EntityResolutionStatus.MISSING
        assert ref.resolved_entity_id is None
        assert ref.confidence == 0.0

    def test_add_relationship(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        continuity = WorldContinuity(memory)
        continuity.add_relationship(project_id, "Alice", "Room")
        state = continuity.get_world_state(project_id)
        assert "Alice" in state.relationship_graph
        assert "Room" in state.relationship_graph["Alice"]

    def test_entity_from_memory(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        entity = ProjectEntity(
            entity_id=uuid4(),
            entity_type=EntityType.LOCATION,
            name="Forest",
            properties={"lighting": "dusk"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        memory.add_entity(project_id, entity)
        continuity = WorldContinuity(memory)
        retrieved = continuity.get_entity_from_memory(project_id, entity.entity_id)
        assert retrieved is not None
        assert retrieved.name == "Forest"
