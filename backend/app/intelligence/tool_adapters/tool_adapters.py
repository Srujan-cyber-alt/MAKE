"""
MAKE Autonomous Agent Core V2 — Tool Adapters.

Clean adapters for frozen Image and Video systems.
Do NOT import internal implementation details from frozen systems.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum


class ToolCapability(str, Enum):
    GENERATE = "generate"
    EDIT = "edit"
    INSPECT = "inspect"
    STATUS = "status"
    CANCEL = "cancel"


class ToolStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ToolRequest:
    capability: ToolCapability
    parameters: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None


@dataclass
class ToolResult:
    success: bool
    capability: ToolCapability
    artifact_id: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status: ToolStatus = ToolStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolAdapter(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self._status = ToolStatus.IDLE
        self._capabilities: List[ToolCapability] = []

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> ToolStatus:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        raise NotImplementedError

    def cancel(self, idempotency_key: Optional[str] = None) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.CANCEL,
            status=ToolStatus.IDLE,
        )


class ImageToolAdapter(ToolAdapter):
    def __init__(self) -> None:
        super().__init__("image")
        self._capabilities = [ToolCapability.GENERATE, ToolCapability.EDIT, ToolCapability.INSPECT, ToolCapability.STATUS, ToolCapability.CANCEL]

    async def execute(self, request: ToolRequest) -> ToolResult:
        self._status = ToolStatus.BUSY
        try:
            if request.capability == ToolCapability.GENERATE:
                return await self._generate(request)
            elif request.capability == ToolCapability.EDIT:
                return await self._edit(request)
            elif request.capability == ToolCapability.INSPECT:
                return await self._inspect(request)
            elif request.capability == ToolCapability.STATUS:
                return ToolResult(success=True, capability=ToolCapability.STATUS, status=self._status)
            elif request.capability == ToolCapability.CANCEL:
                return self.cancel(request.idempotency_key)
            else:
                return ToolResult(success=False, capability=request.capability, error=f"Unsupported capability: {request.capability}")
        finally:
            self._status = ToolStatus.IDLE

    async def _generate(self, request: ToolRequest) -> ToolResult:
        # Adapter boundary - does not import internal Image implementation
        return ToolResult(
            success=True,
            capability=ToolCapability.GENERATE,
            artifact_id=str(UUID(int=0)),
            output={"type": "image", "status": "generated"},
            status=ToolStatus.IDLE,
        )

    async def _edit(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.EDIT,
            artifact_id=str(UUID(int=0)),
            output={"type": "image", "status": "edited"},
            status=ToolStatus.IDLE,
        )

    async def _inspect(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.INSPECT,
            output={"type": "image", "inspection": "completed"},
            status=ToolStatus.IDLE,
        )

    def get_status(self) -> ToolStatus:
        return self._status

    def get_capabilities(self) -> List[ToolCapability]:
        return list(self._capabilities)


class VideoToolAdapter(ToolAdapter):
    def __init__(self) -> None:
        super().__init__("video")
        self._capabilities = [ToolCapability.GENERATE, ToolCapability.EDIT, ToolCapability.INSPECT, ToolCapability.STATUS, ToolCapability.CANCEL]

    async def execute(self, request: ToolRequest) -> ToolResult:
        self._status = ToolStatus.BUSY
        try:
            if request.capability == ToolCapability.GENERATE:
                return await self._generate(request)
            elif request.capability == ToolCapability.EDIT:
                return await self._edit(request)
            elif request.capability == ToolCapability.INSPECT:
                return await self._inspect(request)
            elif request.capability == ToolCapability.STATUS:
                return ToolResult(success=True, capability=ToolCapability.STATUS, status=self._status)
            elif request.capability == ToolCapability.CANCEL:
                return self.cancel(request.idempotency_key)
            else:
                return ToolResult(success=False, capability=request.capability, error=f"Unsupported capability: {request.capability}")
        finally:
            self._status = ToolStatus.IDLE

    async def _generate(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.GENERATE,
            artifact_id=str(UUID(int=0)),
            output={"type": "video", "status": "generated"},
            status=ToolStatus.IDLE,
        )

    async def _edit(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.EDIT,
            artifact_id=str(UUID(int=0)),
            output={"type": "video", "status": "edited"},
            status=ToolStatus.IDLE,
        )

    async def _inspect(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            success=True,
            capability=ToolCapability.INSPECT,
            output={"type": "video", "inspection": "completed"},
            status=ToolStatus.IDLE,
        )

    def get_status(self) -> ToolStatus:
        return self._status

    def get_capabilities(self) -> List[ToolCapability]:
        return list(self._capabilities)


class ToolRouter:
    def __init__(self) -> None:
        self._adapters: Dict[str, ToolAdapter] = {}

    def register_adapter(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get_adapter(self, tool_name: str) -> Optional[ToolAdapter]:
        return self._adapters.get(tool_name)

    async def execute(self, tool_name: str, request: ToolRequest) -> ToolResult:
        adapter = self._adapters.get(tool_name)
        if not adapter:
            return ToolResult(success=False, capability=request.capability, error=f"Tool not found: {tool_name}")
        return await adapter.execute(request)

    def get_available_tools(self) -> List[str]:
        return list(self._adapters.keys())
