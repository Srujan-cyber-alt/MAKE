from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CONCURRENCY = "concurrency"
    API_CALLS = "api_calls"


@dataclass
class ResourceRequest:
    cpu_cores: float = 0.0
    memory_mb: int = 0
    disk_mb: int = 0
    network_mb: float = 0.0
    concurrency: int = 1
    api_calls: int = 0


@dataclass
class ResourceSnapshot:
    cpu_available: float = 0.0
    memory_available_mb: int = 0
    disk_available_mb: int = 0
    concurrency_available: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceLimit:
    resource_type: ResourceType
    max_value: float
    current: float = 0.0


class ResourceManager:
    def __init__(self) -> None:
        self._limits: Dict[ResourceType, ResourceLimit] = {}
        self._reserved: ResourceRequest = ResourceRequest()
        self._semaphores: Dict[ResourceType, asyncio.Semaphore] = {}

    def set_limit(self, resource_type: ResourceType, limit: ResourceLimit) -> None:
        self._limits[resource_type] = limit
        if resource_type == ResourceType.CONCURRENCY:
            self._semaphores[resource_type] = asyncio.Semaphore(int(limit.max_value))

    def get_limit(self, resource_type: ResourceType) -> Optional[ResourceLimit]:
        return self._limits.get(resource_type)

    def check_availability(self, request: ResourceRequest) -> bool:
        if ResourceType.CONCURRENCY in self._limits:
            limit = self._limits[ResourceType.CONCURRENCY]
            if self._reserved.concurrency + request.concurrency > limit.max_value:
                return False
        return True

    def reserve(self, request: ResourceRequest) -> bool:
        if not self.check_availability(request):
            return False
        self._reserved.concurrency += request.concurrency
        return True

    def release(self, request: ResourceRequest) -> None:
        self._reserved.concurrency = max(0, self._reserved.concurrency - request.concurrency)

    def get_snapshot(self) -> ResourceSnapshot:
        if HAS_PSUTIL:
            cpu = psutil.cpu_count()
            mem = psutil.virtual_memory()
            return ResourceSnapshot(
                cpu_available=float(cpu) if cpu else 4.0,
                memory_available_mb=int(mem.available / 1024 / 1024) if mem else 8192,
                disk_available_mb=100000,
                concurrency_available=max(0, 4 - self._reserved.concurrency),
            )
        return ResourceSnapshot(
            cpu_available=4.0,
            memory_available_mb=8192,
            disk_available_mb=100000,
            concurrency_available=max(0, 4 - self._reserved.concurrency),
        )
