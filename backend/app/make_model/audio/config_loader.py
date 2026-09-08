"""
Audio configuration loader.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import json

from app.make_model.audio.architecture import AudioConfig


def load_audio_config(config_path: str | Path) -> AudioConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio config not found: {config_path}")
    return AudioConfig.from_json(path)


def get_default_config(model_size: str = "tiny") -> AudioConfig:
    from app.make_model.utils import paths as make_paths
    import os
    config_dir = Path(__file__).parent / "configs"
    config_file = config_dir / f"audio_{model_size}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"No config for model size: {model_size}")
    return load_audio_config(config_file)
