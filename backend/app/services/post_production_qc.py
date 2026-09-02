"""
Quality Control Integration for MAKE AI Video Phase 17.

Post-production quality checks for timeline outputs.
"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class PostProductionQC:
    def check_render_output(self, output_path: str, expected_duration: float = None, expected_resolution: tuple = None, expected_fps: int = None) -> Dict[str, Any]:
        issues = []
        from app.services.result_validator import ResultValidator
        validator = ResultValidator()
        validation = validator.validate_output(output_path, expected_duration, expected_resolution[0] if expected_resolution else None, expected_resolution[1] if expected_resolution else None)
        if not validation.valid:
            issues.extend(validation.errors or [])
        return {
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "validation": validation.__dict__ if hasattr(validation, "__dict__") else str(validation),
            "score": 1.0 if not issues else 0.0,
        }

    def check_caption_bounds(self, resolution: tuple, captions: List[Dict[str, Any]]) -> List[str]:
        issues = []
        w, h = resolution
        for cap in captions:
            if cap.get("y", 0) < 0 or cap.get("y", 0) > h:
                issues.append(f"Caption {cap.get('segment_id')} out of vertical bounds")
        return issues

    def check_graphics_bounds(self, resolution: tuple, graphics: List[Dict[str, Any]]) -> List[str]:
        issues = []
        w, h = resolution
        for g in graphics:
            if g.get("x", 0) < 0 or g.get("x", 0) > w:
                issues.append(f"Graphic {g.get('graphic_id')} out of horizontal bounds")
        return issues


post_production_qc = PostProductionQC()
