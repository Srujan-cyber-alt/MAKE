"""MAKE Audio — Architecture: component base class and capability registry.

All audio modules inherit ``AudioComponent`` and register themselves on
``AudioArchitecture`` so capabilities can be discovered at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Dict, List, Any

from app.make_model.audio.wav import AudioBuffer
from app.make_model.audio.config import AudioConfig


class AudioComponent(ABC):
    """Base class for all audio processing components."""

    name: str = "base"
    description: str = "Audio component"

    def __init__(self, config: AudioConfig | None = None):
        self.config = config or AudioConfig()

    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Process audio or synthesize audio. Concrete implementation required."""
        raise NotImplementedError


class AudioArchitecture:
    """Central registry for all audio capabilities."""

    _components: Dict[str, Type[AudioComponent]] = {}
    _instances: Dict[str, AudioComponent] = {}

    @classmethod
    def register(cls, name: str, component_class: Type[AudioComponent]) -> None:
        cls._components[name] = component_class

    @classmethod
    def get_class(cls, name: str) -> Type[AudioComponent] | None:
        return cls._components.get(name)

    @classmethod
    def get(cls, name: str) -> AudioComponent | None:
        if name not in cls._instances:
            cls_cls = cls._components.get(name)
            if cls_cls is None:
                return None
            cls._instances[name] = cls_cls()
        return cls._instances[name]

    @classmethod
    def list_capabilities(cls) -> List[str]:
        return sorted(cls._components.keys())

    @classmethod
    def reset(cls) -> None:
        cls._instances.clear()
