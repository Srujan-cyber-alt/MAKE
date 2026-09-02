"""
Provenance Tracker for MAKE AI Video Phase 16.

Records complete provenance for every generated asset.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    def __init__(self):
        self._provenance: Dict[str, Dict[str, Any]] = {}

    def record_provenance(self, asset_id: str, provenance: Dict[str, Any]):
        entry = {
            "asset_id": asset_id,
            "timestamp": datetime.utcnow().isoformat(),
            **provenance,
        }
        self._provenance[asset_id] = entry
        logger.info(f"Provenance recorded for asset {asset_id}")

    def get_provenance(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return self._provenance.get(asset_id)

    def build_provenance(self, source_project: str, source_prompt: str, provider: str, model: str, model_version: str, generation_mode: str, references: List[Dict], generation_job: str, parameters: Dict[str, Any], routing_decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_project": source_project,
            "source_prompt": source_prompt,
            "provider": provider,
            "model": model,
            "model_version": model_version,
            "generation_mode": generation_mode,
            "references": references,
            "generation_job": generation_job,
            "timestamp": datetime.utcnow().isoformat(),
            "parameters": parameters,
            "routing_decision": routing_decision,
        }


provenance_tracker = ProvenanceTracker()
