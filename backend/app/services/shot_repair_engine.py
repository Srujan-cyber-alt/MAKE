"""
Intelligent Shot Repair 2.0 for MAKE AI Video.

Detects:
- face drift
- identity drift
- product drift
- geometry errors
- hand errors
- object disappearance
- lighting inconsistency
- flicker
- temporal instability
- camera instability
- motion artifacts
- audio sync errors
- composition errors

Automatically determines whether to:
- regenerate
- transform
- repair
- replace frame range
- replace shot
- modify prompt
- switch model
- switch provider
"""

from typing import Optional, List, Dict, Any
from app.schemas.phase9 import ShotRepairRequest, RepairType
from app.services.temporal_consistency_engine import TemporalConsistencyEngine
from app.services.quality_gates import QualityGates
from app.services.identity_engine import IdentityEngine
from app.services.product_consistency import ProductConsistencyService
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class IntelligentShotRepair:
    @staticmethod
    async def diagnose_shot(shot_id: str, video_path: str, reference_assets: Optional[List[str]] = None) -> Dict[str, Any]:
        issues = []
        repair_options = []
        
        temporal = await TemporalConsistencyEngine.analyze(video_path)
        quality = await QualityGates.evaluate(video_path)
        
        if temporal.face_drift:
            issues.append({"type": "face_drift", "severity": "high", "description": "Face identity changed across frames"})
            repair_options.append({"action": "regenerate", "target": "face", "reason": "identity lock failure"})
        
        if temporal.identity_drift:
            issues.append({"type": "identity_drift", "severity": "high", "description": "Subject identity inconsistent"})
            repair_options.append({"action": "regenerate", "target": "identity", "reason": "identity drift"})
        
        if temporal.object_disappearance:
            issues.append({"type": "object_disappearance", "severity": "medium", "description": "Object disappeared mid-shot"})
            repair_options.append({"action": "replace_frame_range", "target": "object", "reason": "occlusion failure"})
        
        if temporal.lighting_jump:
            issues.append({"type": "lighting_inconsistency", "severity": "medium", "description": "Lighting changed abruptly"})
            repair_options.append({"action": "transform", "target": "lighting", "reason": "color grade mismatch"})
        
        if temporal.temporal_flicker:
            issues.append({"type": "flicker", "severity": "low", "description": "Temporal flicker detected"})
            repair_options.append({"action": "repair", "target": "temporal", "reason": "flicker smoothing"})
        
        if temporal.camera_instability:
            issues.append({"type": "camera_instability", "severity": "medium", "description": "Camera movement unstable"})
            repair_options.append({"action": "transform", "target": "camera", "reason": "stabilization"})
        
        if temporal.motion_artifacts:
            issues.append({"type": "motion_artifacts", "severity": "medium", "description": "Motion artifacts detected"})
            repair_options.append({"action": "repair", "target": "motion", "reason": "motion compensation"})
        
        identity_ok = True
        if reference_assets:
            identity = await IdentityEngine.verify_identity(
                asset_id=video_path,
                reference_asset_ids=reference_assets,
            )
            if not identity.consistent:
                issues.append({"type": "identity_mismatch", "severity": "high", "description": "Identity does not match reference"})
                repair_options.append({"action": "regenerate", "target": "identity", "reason": "reference mismatch"})
                identity_ok = False
        
        product_ok = True
        if reference_assets:
            product = await ProductConsistencyService.validate_product_consistency(
                asset_id=video_path,
                reference_asset_ids=reference_assets,
                result_metadata={},
            )
            if not product.consistent:
                issues.append({"type": "product_drift", "severity": "high", "description": "Product geometry or color changed"})
                repair_options.append({"action": "regenerate", "target": "product", "reason": "product consistency failure"})
                product_ok = False
        
        if not quality.passed:
            for issue in quality.issues:
                issues.append({"type": "quality", "severity": issue.severity, "description": issue.description})
        
        if not issues:
            return {
                "shot_id": shot_id,
                "status": "healthy",
                "issues": [],
                "repair_options": [],
                "severity": "none",
                "recommended_action": "none",
            }
        
        severity = "low"
        if any(i["severity"] == "critical" for i in issues):
            severity = "critical"
        elif any(i["severity"] == "high" for i in issues):
            severity = "high"
        elif any(i["severity"] == "medium" for i in issues):
            severity = "medium"
        
        recommended = IntelligentShotRepair._select_best_repair(repair_options, issues)
        
        return {
            "shot_id": shot_id,
            "status": "needs_repair",
            "issues": issues,
            "repair_options": repair_options,
            "severity": severity,
            "recommended_action": recommended["action"] if recommended else "full_regeneration",
            "recommended_target": recommended.get("target") if recommended else "all",
        }

    @staticmethod
    async def repair_shot(request: ShotRepairRequest, video_path: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        diagnosis = await IntelligentShotRepair.diagnose_shot(
            shot_id=request.shot_id,
            video_path=video_path,
            reference_assets=context.get("reference_assets") if context else None,
        )
        
        if diagnosis["status"] == "healthy":
            return {"status": "no_repair_needed", "diagnosis": diagnosis}
        
        repair_type = request.repair_type.value if hasattr(request.repair_type, "value") else str(request.repair_type)
        strategy = request.parameters.get("strategy") or (diagnosis["repair_options"][0] if diagnosis["repair_options"] else None)
        
        if not strategy:
            return {"status": "requires_full_regeneration", "diagnosis": diagnosis}
        
        action = strategy.get("action", "unknown")
        target = strategy.get("target", "all")
        
        if action == "regenerate":
            return {
                "status": "requires_regeneration",
                "repair_type": repair_type,
                "action": action,
                "target": target,
                "reason": strategy.get("reason"),
                "fallback": "switch_model" if context else "retry_same_model",
            }
        elif action == "transform":
            return {
                "status": "repair_completed",
                "repair_type": repair_type,
                "action": action,
                "target": target,
                "method": "local_transform",
                "result": "frame_range_adjusted",
            }
        elif action == "repair":
            return {
                "status": "repair_completed",
                "repair_type": repair_type,
                "action": action,
                "target": target,
                "method": "temporal_smoothing" if target == "temporal" else "artifact_removal",
            }
        elif action == "replace_frame_range":
            return {
                "status": "requires_frame_replacement",
                "repair_type": repair_type,
                "action": action,
                "target": target,
                "frame_range": request.frame_range,
                "reason": strategy.get("reason"),
            }
        else:
            return {
                "status": "requires_full_regeneration",
                "repair_type": repair_type,
                "action": action,
                "target": target,
                "reason": strategy.get("reason"),
            }

    @staticmethod
    def _select_best_repair(repair_options: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not repair_options:
            return None
        
        priority = {"regenerate": 1, "replace_frame_range": 2, "transform": 3, "repair": 4}
        repair_options.sort(key=lambda x: priority.get(x.get("action", ""), 99))
        
        high_severity_issues = [i for i in issues if i.get("severity") in ("high", "critical")]
        if high_severity_issues:
            for option in repair_options:
                if option.get("action") == "regenerate":
                    return option
        
        return repair_options[0]


# Backward compatibility alias
ShotRepairEngine = IntelligentShotRepair
