"""Tests for the Reality Graph."""

import pytest

from app.intelligence.core.reality_graph import RealityGraph
from app.intelligence.schemas import GraphNodeRecord, GraphEdgeRecord


class TestRealityGraph:
    @pytest.fixture
    def graph(self, intel_db):
        return RealityGraph()

    @pytest.mark.asyncio
    async def test_add_and_get_node(self, graph):
        node = await graph.add_node("Alice", "Person", {"age": 30})
        assert node.id is not None
        assert node.name == "Alice"
        assert node.entity_type == "Person"

        retrieved = await graph.get_node(node.id)
        assert retrieved is not None
        assert retrieved.name == "Alice"

    @pytest.mark.asyncio
    async def test_find_nodes_by_type(self, graph):
        await graph.add_node("Alice", "Person", {})
        await graph.add_node("Camera", "Object", {})
        await graph.add_node("Car", "Object", {})
        results = await graph.find_nodes(entity_type="Object")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_nodes_by_name(self, graph):
        await graph.add_node("Alice", "Person", {})
        results = await graph.find_nodes(name="Ali")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_add_and_query_edges(self, graph):
        src = await graph.add_node("Alice", "Person", {})
        tgt = await graph.add_node("Camera", "Object", {})
        edge = await graph.add_edge(src.id, tgt.id, "owns", weight=1.0)
        assert edge.id is not None
        assert edge.source_node_id == src.id
        assert edge.target_node_id == tgt.id
        assert edge.relation_type == "owns"

    @pytest.mark.asyncio
    async def test_get_edges(self, graph):
        alice = await graph.add_node("Alice", "Person", {})
        camera = await graph.add_node("Camera", "Object", {})
        car = await graph.add_node("Car", "Object", {})
        await graph.add_edge(alice.id, camera.id, "owns")
        await graph.add_edge(alice.id, car.id, "owns")

        edges = await graph.get_edges(source_node_id=alice.id)
        assert len(edges) == 2

    @pytest.mark.asyncio
    async def test_get_neighbors_out_direction(self, graph):
        alice = await graph.add_node("Alice", "Person", {})
        camera = await graph.add_node("Camera", "Object", {})
        car = await graph.add_node("Car", "Object", {})
        await graph.add_edge(alice.id, camera.id, "owns")
        await graph.add_edge(alice.id, car.id, "owns")

        neighbors = await graph.get_neighbors(alice.id, direction="out")
        names = {n.name for n in neighbors}
        assert "Camera" in names
        assert "Car" in names

    @pytest.mark.asyncio
    async def test_traverse_graph(self, graph):
        alice = await graph.add_node("Alice", "Person", {})
        camera = await graph.add_node("Camera", "Object", {})
        photo = await graph.add_node("Photo", "Asset", {})
        await graph.add_edge(alice.id, camera.id, "owns")
        await graph.add_edge(camera.id, photo.id, "captured")

        results = await graph.traverse(alice.id, max_depth=2)
        target_names = {r["target_node"]["name"] for r in results}
        assert "Camera" in target_names
        assert "Photo" in target_names

    @pytest.mark.asyncio
    async def test_edge_to_nonexistent_node_fails(self, graph):
        with pytest.raises(ValueError):
            await graph.add_edge("nope1", "nope2", "owns")

    @pytest.mark.asyncio
    async def test_delete_node(self, graph):
        node = await graph.add_node("Temp", "Object", {})
        deleted = await graph.delete_node(node.id)
        assert deleted is True
        retrieved = await graph.get_node(node.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_clear_all(self, graph):
        await graph.add_node("Alice", "Person", {})
        count = await graph.clear_all()
        assert count > 0

    @pytest.mark.asyncio
    async def test_extensible_relation_types(self, graph):
        """Test that arbitrary extensible relationship types work."""
        a = await graph.add_node("ProjectA", "Project", {})
        b = await graph.add_node("Asset1", "Asset", {})
        edge = await graph.add_edge(a.id, b.id, "custom_relation_type", weight=0.5, attributes={"note": "test"})
        assert edge.relation_type == "custom_relation_type"
        edges = await graph.get_edges(relation_type="custom_relation_type")
        assert len(edges) == 1
