"""Tests for MAKE Autonomous Agent Core V2 — Project Memory."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.project_memory import (
    ProjectMemory,
    ProjectEntity,
    EntityType,
    MemoryAction,
)


class TestProjectMemory:
    def test_create_project(self):
        memory = ProjectMemory()
        project_id = uuid4()
        state = memory.create_project(project_id, {"name": "test"})
        assert state.project_id == project_id
        assert len(state.entities) == 0
        assert len(state.versions) == 1

    def test_add_entity(self):
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
        retrieved = memory.get_entity(project_id, entity.entity_id)
        assert retrieved is not None
        assert retrieved.name == "Alice"
        assert retrieved.properties["hair"] == "blonde"

    def test_update_entity(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        entity = ProjectEntity(
            entity_id=uuid4(),
            entity_type=EntityType.LOCATION,
            name="Room",
            properties={"size": "small"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        memory.add_entity(project_id, entity)
        updated = memory.update_entity(project_id, entity.entity_id, {"size": "large"})
        assert updated.properties["size"] == "large"
        assert updated.version == 2

    def test_list_entities_by_type(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        char1 = ProjectEntity(uuid4(), EntityType.CHARACTER, "Alice", {}, datetime.utcnow(), datetime.utcnow())
        char2 = ProjectEntity(uuid4(), EntityType.CHARACTER, "Bob", {}, datetime.utcnow(), datetime.utcnow())
        loc1 = ProjectEntity(uuid4(), EntityType.LOCATION, "Room", {}, datetime.utcnow(), datetime.utcnow())
        memory.add_entity(project_id, char1)
        memory.add_entity(project_id, char2)
        memory.add_entity(project_id, loc1)
        characters = memory.list_entities(project_id, EntityType.CHARACTER)
        assert len(characters) == 2
        locations = memory.list_entities(project_id, EntityType.LOCATION)
        assert len(locations) == 1

    def test_rollback(self):
        memory = ProjectMemory()
        project_id = uuid4()
        state = memory.create_project(project_id)
        entity = ProjectEntity(
            entity_id=uuid4(),
            entity_type=EntityType.OBJECT,
            name="Sword",
            properties={"material": "iron"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        memory.add_entity(project_id, entity)
        v1 = state.versions[-1].version_id
        memory.update_entity(project_id, entity.entity_id, {"material": "steel"})
        rolled = memory.rollback(project_id, v1)
        assert rolled is not None
        assert rolled.entities[str(entity.entity_id)].properties["material"] == "iron"

    def test_versions_recorded(self):
        memory = ProjectMemory()
        project_id = uuid4()
        memory.create_project(project_id)
        versions = memory.get_versions(project_id)
        assert len(versions) == 1
        assert versions[0].action == MemoryAction.CREATE
