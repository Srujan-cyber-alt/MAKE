"""
MAKE Intelligence Core ToolAdapter for Audio subsystem.

Provides abstract interfaces for:
  audio.generate
  audio.voice
  audio.dialogue
  audio.transform
  audio.edit
  audio.repair
  audio.foley
  audio.soundscape
  audio.music
  audio.mix

Does NOT import internal Audio implementation details.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from app.intelligence.agent.agent_roles import AgentRole, RoleCapability


class AudioCapability(str, Enum):
    GENERATE = "audio.generate"
    VOICE = "audio.voice"
    DIALOGUE = "audio.dialogue"
    TRANSFORM = "audio.transform"
    EDIT = "audio.edit"
    REPAIR = "audio.repair"
    FOLEY = "audio.foley"
    SOUNDSCAPE = "audio.soundscape"
    MUSIC = "audio.music"
    MIX = "audio.mix"


@dataclass
class AudioToolRequest:
    capability: AudioCapability
    parameters: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioToolResult:
    success: bool
    capability: AudioCapability
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    quality: Optional[Dict[str, Any]] = None


class AudioToolAdapter:
    def __init__(self) -> None:
        self._capabilities: Dict[AudioCapability, Any] = {}

    def register_capability(self, capability: AudioCapability, handler: Any) -> None:
        self._capabilities[capability] = handler

    async def execute(self, request: AudioToolRequest) -> AudioToolResult:
        handler = self._capabilities.get(request.capability)
        if not handler:
            return AudioToolResult(
                success=False,
                capability=request.capability,
                error=f"Capability not registered: {request.capability}",
            )
        try:
            output = await handler(request.parameters)
            return AudioToolResult(
                success=True,
                capability=request.capability,
                output=output,
                provenance={"adapter": "intelligence_audio_tool_adapter"},
            )
        except Exception as e:
            return AudioToolResult(
                success=False,
                capability=request.capability,
                error=str(e),
            )

    def get_available_capabilities(self) -> List[AudioCapability]:
        return list(self._capabilities.keys())


class AudioAgentRole(AgentRole):
    def __init__(self) -> None:
        super().__init__("audio", [
            RoleCapability.PLAN,
            RoleCapability.EXECUTE,
            RoleCapability.OBSERVE,
            RoleCapability.EVALUATE,
            RoleCapability.VERIFY,
        ])
        self.adapter = AudioToolAdapter()

    def can_handle(self, capability: AudioCapability) -> bool:
        return capability in self.adapter.get_available_capabilities()

    async def handle_request(self, request: AudioToolRequest) -> AudioToolResult:
        return await self.adapter.execute(request)
