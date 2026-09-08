"""Tests for World Memory."""

import pytest

from app.intelligence.core.world_memory import WorldMemory
from app.intelligence.schemas import EntityType, RelationType


class TestWorldMemory:
    @pytest.fixture
    def wm(self, intel_db):
        return WorldMemory()

    @pytest.mark.asyncio
    async def test_store_and_retrieve_entity(self, wm):
        record = await wm.store_entity(
            EntityType.PERSON, "Alice", {"age": 30}, consent=True
        )
        assert record.id is not None
        assert record.name == "Alice"
        assert record.entity_type == EntityType.PERSON

        retrieved = await wm.get_entity(record.id)
        assert retrieved is not None
        assert retrieved.name == "Alice"

    @pytest.mark.asyncio
    async def test_store_without_consent_fails(self, wm):
        with pytest.raises(PermissionError):
            await wm.store_entity(
                EntityType.PERSON, "Bob", consent=False
            )

    @pytest.mark.asyncio
    async def test_find_entities_by_type(self, wm):
        await wm.store_entity(EntityType.OBJECT, "Car", consent=True)
        await wm.store_entity(EntityType.PERSON, "Driver", consent=True)
        results = await wm.find_entities(entity_type=EntityType.PERSON)
        assert len(results) == 1
        assert results[0].name == "Driver"

    @pytest.mark.asyncio
    async def test_find_by_name(self, wm):
        await wm.store_entity(EntityType.PERSON, "Alice", consent=True)
        await wm.store_entity(EntityType.PERSON, "Bob", consent=True)
        results = await wm.find_entities(name="Alice")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_update_entity(self, wm):
        record = await wm.store_entity(EntityType.OBJECT, "Camera", {"model": "X1"}, consent=True)
        updated = await wm.update_entity(record.id, attributes={"model": "X2", "lens": "50mm"})
        assert updated is not None
        assert updated.attributes["model"] == "X2"
        assert updated.attributes["lens"] == "50mm"

    @pytest.mark.asyncio
    async def test_delete_entity(self, wm):
        record = await wm.store_entity(EntityType.OBJECT, "Lens", consent=True)
        deleted = await wm.delete_entity(record.id)
        assert deleted is True
        retrieved = await wm.get_entity(record.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_relation_between_entities(self, wm):
        src = await wm.store_entity(EntityType.PERSON, "Alice", consent=True)
        tgt = await wm.store_entity(EntityType.OBJECT, "Camera", consent=True)
        rel_id = await wm.add_relation(src.id, tgt.id, RelationType.OWNS)
        assert rel_id is not None

    @pytest.mark.asyncio
    async def test_get_related_entities(self, wm):
        alice = await wm.store_entity(EntityType.PERSON, "Alice", consent=True)
        camera = await wm.store_entity(EntityType.OBJECT, "Camera", consent=True)
        await wm.add_relation(alice.id, camera.id, RelationType.OWNS)

        related = await wm.get_related(alice.id, relation_types=[RelationType.OWNS])
        assert len(related) == 1
        assert related[0]["name"] == "Camera"

    @pytest.mark.asyncio
    async def test_count_entities(self, wm):
        await wm.store_entity(EntityType.PERSON, "Alice", consent=True)
        await wm.store_entity(EntityType.PERSON, "Bob", consent=True)
        count = await wm.count_entities()
        assert count == 2

    @pytest.mark.asyncio
    async def test_scope_isolation(self, wm):
        await wm.store_entity(EntityType.PERSON, "Alice", consent=True, scope="user1")
        await wm.store_entity(EntityType.PERSON, "Bob", consent=True, scope="user2")
        results = await wm.find_entities(scope="user1")
        assert len(results) == 1
        assert results[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_update_with_id(self, wm):
        record = await wm.store_entity(EntityType.OBJECT, "Camera", consent=True)
        await wm.store_entity(
            EntityType.OBJECT, "Camera v2", {"model": "X2"},
            consent=True, entity_id=record.id, update=True
        )
        updated = await wm.get_entity(record.id)
        assert updated.name == "Camera v2"
