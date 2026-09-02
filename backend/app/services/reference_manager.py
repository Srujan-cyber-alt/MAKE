"""
Reference Manager for MAKE AI Video Phase 16.

Universal reference handling across all providers.
"""

from typing import Optional, Dict, List, Any
import logging
import os
import shutil

logger = logging.getLogger(__name__)


class ReferenceManager:
    def __init__(self, storage_service=None):
        self.storage = storage_service

    def prepare_references(self, references: List[Dict[str, Any]], model_id: str, provider_id: str) -> Dict[str, Any]:
        from app.services.universal_model_registry import UniversalModelRegistry
        registry = UniversalModelRegistry.get_instance()
        model = registry.get_model(model_id) if registry else None

        if not model:
            return {"prepared": False, "error": "Model not found", "references": []}

        max_refs = model.reference_limits.get("max_reference_images", model.limits.max_reference_images)
        supported_types = model.reference_limits.get("supported_types", [])

        prepared = []
        unsupported = []
        for ref in references:
            ref_type = ref.get("type", "image")
            if supported_types and ref_type not in supported_types:
                unsupported.append(ref)
                continue
            prepared.append({
                "type": ref_type,
                "url": ref.get("url"),
                "asset_id": ref.get("asset_id"),
                "role": ref.get("role", "reference"),
                "order": ref.get("order", len(prepared)),
            })

        if len(prepared) > max_refs:
            prepared = prepared[:max_refs]

        return {
            "prepared": True,
            "references": prepared,
            "unsupported": unsupported,
            "truncated": len(references) > max_refs,
            "total_submitted": len(prepared),
        }

    def validate_reference(self, reference: Dict[str, Any]) -> Dict[str, Any]:
        ref_type = reference.get("type", "image")
        url = reference.get("url")
        asset_id = reference.get("asset_id")

        if not url and not asset_id:
            return {"valid": False, "error": "Reference must have url or asset_id"}

        return {"valid": True, "type": ref_type}

    def prepare_first_last_frame(self, first_frame: Dict[str, Any] = None, last_frame: Dict[str, Any] = None, model_id: str = None) -> Dict[str, Any]:
        result = {}
        if first_frame:
            result["first_frame"] = self.prepare_references([first_frame], model_id, "").get("references", [{}])[0] if first_frame else None
        if last_frame:
            result["last_frame"] = self.prepare_references([last_frame], model_id, "").get("references", [{}])[0] if last_frame else None
        return result


reference_manager = ReferenceManager()
