"""
Model Versioning for MAKE AI Video Phase 16.

Tracks model versions for reproducibility.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModelVersioning:
    def __init__(self):
        self._versions: Dict[str, Dict[str, Any]] = {}

    def record_version(self, model_id: str, provider_id: str, version: str, capability_snapshot: Dict[str, Any]):
        key = f"{provider_id}:{model_id}"
        self._versions[key] = {
            "model_id": model_id,
            "provider_id": provider_id,
            "version": version,
            "capability_snapshot": capability_snapshot,
            "recorded_at": datetime.utcnow().isoformat(),
        }

    def get_version(self, model_id: str, provider_id: str) -> Optional[Dict[str, Any]]:
        key = f"{provider_id}:{model_id}"
        return self._versions.get(key)

    def get_capability_snapshot(self, model_id: str, provider_id: str) -> Dict[str, Any]:
        version = self.get_version(model_id, provider_id)
        if version:
            return version.get("capability_snapshot", {})
        return {}


model_versioning = ModelVersioning()
