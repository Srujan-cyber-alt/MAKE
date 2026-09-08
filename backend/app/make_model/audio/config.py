"""MAKE Audio — Configuration management.

Provides typed config dataclasses and JSON loading for tiny / research /
production model configurations.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class AudioConfig:
    sample_rate: int = 22050
    bit_depth: int = 16
    channels: int = 1
    frame_rate: int = 50
    hop_length: int = 256
    n_fft: int = 512
    max_duration_seconds: float = 60.0


@dataclass
class ModelConfig:
    name: str
    sample_rate: int
    bit_depth: int
    channels: int
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelConfig":
        return cls(
            name=d.get("name", "unnamed"),
            sample_rate=d.get("sample_rate", 22050),
            bit_depth=d.get("bit_depth", 16),
            channels=d.get("channels", 1),
            description=d.get("description", ""),
            parameters=d.get("parameters", {}),
        )


TINY = ModelConfig(
    name="audio_tiny",
    sample_rate=8000,
    bit_depth=16,
    channels=1,
    description="CPU-runnable reference model (8 kHz mono).",
    parameters={
        "formants": 3,
        "max_harmonics": 8,
        "noise_shaping": True,
        "deterministic": True,
        "training_required_gpus": 0,
    },
)

RESEARCH = ModelConfig(
    name="audio_research",
    sample_rate=22050,
    bit_depth=16,
    channels=1,
    description="Research-scale model (22 kHz).",
    parameters={
        "formants": 5,
        "max_harmonics": 16,
        "noise_shaping": True,
        "deterministic": True,
        "training_required_gpus": 0,
    },
)

PRODUCTION = ModelConfig(
    name="audio_production",
    sample_rate=48000,
    bit_depth=24,
    channels=2,
    description="Production model (48 kHz stereo). Training marked BLOCKED_EXTERNAL (GPU required).",
    parameters={
        "formants": 8,
        "max_harmonics": 48,
        "noise_shaping": True,
        "deterministic": False,
        "training_required_gpus": 1,
    },
)

BY_NAME: Dict[str, ModelConfig] = {
    "audio_tiny": TINY,
    "audio_research": RESEARCH,
    "audio_production": PRODUCTION,
}


_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")


def load_config(name: str) -> ModelConfig:
    """Load a model config by name, falling back to JSON file lookup."""
    if name in BY_NAME:
        return BY_NAME[name]
    path = os.path.join(_CONFIG_DIR, f"{name}.json")
    if os.path.isfile(path):
        with open(path) as f:
            return ModelConfig.from_dict(json.load(f))
    raise FileNotFoundError(f"Audio config not found: {name}")


def get_config(name: str = "audio_tiny") -> ModelConfig:
    return load_config(name)
