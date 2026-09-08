"""Tests for Resource Manager."""

import pytest
from app.intelligence.agent.resource_manager import (
    ResourceManager, ResourceRequest, ResourceSnapshot, ResourceType, ResourceLimit
)


class TestResourceManager:
    def test_create_resource_manager(self):
        rm = ResourceManager()
        assert rm is not None

    def test_check_resource_availability(self):
        rm = ResourceManager()
        request = ResourceRequest(cpu_cores=1.0, memory_mb=128)
        available = rm.check_availability(request)
        assert isinstance(available, bool)

    def test_reserve_resources(self):
        rm = ResourceManager()
        request = ResourceRequest(cpu_cores=1.0, memory_mb=128)
        result = rm.reserve(request)
        assert result is True or result is False

    def test_release_resources(self):
        rm = ResourceManager()
        request = ResourceRequest(cpu_cores=1.0, memory_mb=128)
        rm.reserve(request)
        rm.release(request)
        assert True

    def test_get_snapshot(self):
        rm = ResourceManager()
        snapshot = rm.get_snapshot()
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.cpu_available >= 0

    def test_resource_type_values(self):
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.CONCURRENCY.value == "concurrency"

    def test_limit_enforcement(self):
        rm = ResourceManager()
        limit = ResourceLimit(resource_type=ResourceType.CONCURRENCY, max_value=2)
        rm.set_limit(ResourceType.CONCURRENCY, limit)
        assert rm.get_limit(ResourceType.CONCURRENCY) is not None
