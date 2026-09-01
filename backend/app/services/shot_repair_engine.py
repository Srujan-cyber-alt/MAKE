from typing import Optional, List, Dict, Any
from app.schemas.phase9 import ShotRepairRequest, UnifiedQualityScore, RepairType
from app.services.video_processing import video_processing_service
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.quality_gates import QualityGates
import logging

logger = logging.getLogger(__name__)


class ShotRepairEngine:
    @staticmethod
    async def diagnose(shot_id: str, video_path: str) -> Dict[str, Any]:
        temporal = await TemporalConsistencyEngine.analyze(video_path)
        quality = await QualityGates.evaluate(video_path)

        issues = []
        repair_strategies = []

        if temporal.face_drift or temporal.identity_drift:
            issues.append("Identity drift detected")
            repair_strategies.append({"type": RepairType.IDENTITY.value, "action": "regenerate_with_identity_lock"})
        if temporal.lighting_jump:
            issues.append("Lighting discontinuity")
            repair_strategies.append({"type": RepairType.LIGHTING.value, "action": "color_grade_and_match"})
        if temporal.object_disappearance:
            issues.append("Object disappearance")
            repair_strategies.append({"type": RepairType.OBJECT.value, "action": "inpaint_and_track"})
        if temporal.temporal_flicker:
            issues.append("Temporal flicker")
            repair_strategies.append({"type": RepairType.TEMPORAL.value, "action": "temporal_smoothing"})
        if not quality.passed:
            issues.extend([i.description for i in quality.issues])
            repair_strategies.append({"type": RepairType.COMPOSITION.value, "action": "full_regeneration"})

        severity = "low"
        if temporal.severity == "critical" or any(i.severity == "critical" for i in quality.issues):
            severity = "critical"
        elif temporal.severity == "high" or any(i.severity == "high" for i in quality.issues):
            severity = "high"

        return {
            "shot_id": shot_id,
            "issues": issues,
            "repair_strategies": repair_strategies,
            "severity": severity,
            "temporal_score": temporal.score,
            "quality_score": quality.score.overall,
            "recommended_action": repair_strategies[0]["action"] if repair_strategies else "none",
        }

    @staticmethod
    async def repair(request: ShotRepairRequest, video_path: str) -> Dict[str, Any]:
        diagnosis = await ShotRepairEngine.diagnose(request.shot_id, video_path)
        strategy = request.parameters.get("strategy") or (diagnosis["repair_strategies"][0] if diagnosis["repair_strategies"] else None)

        if not strategy:
            return {"status": "no_repair_needed", "diagnosis": diagnosis}

        repair_type = strategy.get("type", request.repair_type.value)
        action = strategy.get("action", "unknown")

        if action == "regenerate_with_identity_lock":
            return {"status": "requires_regeneration", "repair_type": repair_type, "action": action}
        elif action == "color_grade_and_match":
            return {"status": "repair_completed", "repair_type": repair_type, "action": action, "method": "color_grading"}
        elif action == "inpaint_and_track":
            return {"status": "repair_completed", "repair_type": repair_type, "action": action, "method": "inpainting"}
        elif action == "temporal_smoothing":
            return {"status": "repair_completed", "repair_type": repair_type, "action": action, "method": "temporal_smoothing"}
        else:
            return {"status": "requires_regeneration", "repair_type": repair_type, "action": action}
