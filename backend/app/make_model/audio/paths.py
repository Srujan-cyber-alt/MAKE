"""
Centralized path management for MAKE Audio production.

All persistent production state lives under a configurable base directory.
No /tmp dependencies in production paths.
"""

from __future__ import annotations
from pathlib import Path
import os


def _get_base_dir() -> Path:
    """Get the base directory for all MAKE Audio production data.
    
    Can be overridden with MAKE_AUDIO_DATA_DIR environment variable.
    Defaults to ./data relative to the backend root.
    """
    env_dir = os.environ.get("MAKE_AUDIO_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    
    # Default to backend/data
    backend_root = Path(__file__).resolve().parents[3]  # backend/
    return backend_root / "data"


def get_voice_identities_path() -> Path:
    """Path to voice identities JSON store."""
    return _get_base_dir() / "voice_identities.json"


def get_model_registry_path() -> Path:
    """Path to model registry JSON."""
    return _get_base_dir() / "model_registry.json"


def get_checkpoints_dir() -> Path:
    """Directory for model checkpoints."""
    path = _get_base_dir() / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_dataset_dir() -> Path:
    """Directory for dataset files."""
    path = _get_base_dir() / "datasets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_artifacts_dir() -> Path:
    """Directory for generated audio artifacts."""
    path = _get_base_dir() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """Directory for log files."""
    path = _get_base_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_jobs_dir() -> Path:
    """Directory for job state persistence."""
    path = _get_base_dir() / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    """Directory for configuration files."""
    path = _get_base_dir() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_dir() -> Path:
    """Temporary directory for scratch work (safe to clear on restart)."""
    path = _get_base_dir() / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_all_dirs() -> None:
    """Create all standard directories."""
    get_checkpoints_dir()
    get_dataset_dir()
    get_artifacts_dir()
    get_logs_dir()
    get_jobs_dir()
    get_config_dir()
    get_temp_dir()