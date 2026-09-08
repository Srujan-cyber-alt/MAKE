"""Configuration for the MAKE Intelligence Core."""

from __future__ import annotations

import os
from typing import Optional


class IntelligenceConfig:
    """CPU-first, self-contained configuration for the intelligence core.

    All persistence defaults are overridden in tests via
    :func:`configure` so that tests can use ephemeral databases.
    """

    def __init__(self) -> None:
        self._db_url: str = ""
        self._storage_path: str = ""
        self._configure_defaults()

    def _configure_defaults(self) -> None:
        storage_root = os.environ.get(
            "MAKE_INTELLIGENCE_STORAGE", "/tmp/make-intelligence"
        )
        self._db_url = os.environ.get(
            "MAKE_INTELLIGENCE_DATABASE_URL", f"sqlite+aiosqlite:///{storage_root}/intelligence.db"
        )
        self._storage_path = storage_root

    @property
    def database_url(self) -> str:
        return self._db_url

    @property
    def storage_path(self) -> str:
        return self._storage_path

    @property
    def checkpoint_dir(self) -> str:
        return os.path.join(self._storage_path, "checkpoints")

    @property
    def artifact_dir(self) -> str:
        return os.path.join(self._storage_path, "artifacts")

    @property
    def log_dir(self) -> str:
        return os.path.join(self._storage_path, "logs")

    def configure(
        self,
        database_url: Optional[str] = None,
        storage_path: Optional[str] = None,
    ) -> None:
        """Override configuration (used by tests and runtime initialisation)."""
        if database_url is not None:
            self._db_url = database_url
        if storage_path is not None:
            self._storage_path = storage_path

    def ensure_dirs(self) -> None:
        for d in (self.storage_path, self.checkpoint_dir, self.artifact_dir, self.log_dir):
            os.makedirs(d, exist_ok=True)


intelligence_settings = IntelligenceConfig()
