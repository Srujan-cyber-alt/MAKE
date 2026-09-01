"""
Real Target Selection Workflow for MAKE AI Video.

Supports:
- click-based selection
- point selection
- bounding-box selection
- natural language selection
- ambiguity resolution
- multi-target selection
"""

from typing import Optional, List, Dict, Any
from app.schemas.phase7 import SmartTargetSelection, TargetMatch, TargetCategory, DetectedTarget
from app.services.smart_target_selector import SmartTargetSelector
from app.services.visual_analyzer import VisualAnalyzer
from app.services.redis_service import redis_service
import uuid
import logging

logger = logging.getLogger(__name__)


class TargetSelectionWorkflow:
    @staticmethod
    async def select_target(
        prompt: str,
        asset_id: str,
        project_id: str,
        user_id: str,
        selection_method: str = "auto",
        explicit_target_id: Optional[str] = None,
        point: Optional[Dict[str, float]] = None,
        bbox: Optional[Dict[str, Any]] = None,
        frame_range: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        workflow_id = str(uuid.uuid4())
        logger.info(f"Starting target selection workflow {workflow_id} for prompt: {prompt}")

        analysis = await VisualAnalyzer.analyze_video(
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
            frame_range=frame_range,
        )
        detected_targets = analysis.get("objects", []) + analysis.get("faces", [])

        if explicit_target_id:
            target = next((t for t in detected_targets if t.get("target_id") == explicit_target_id), None)
            if target:
                return {
                    "workflow_id": workflow_id,
                    "method": "explicit",
                    "selected_target": target,
                    "target_id": target.get("target_id"),
                    "confidence": target.get("confidence", 1.0),
                    "ambiguous": False,
                    "alternatives": [],
                }
            return {
                "workflow_id": workflow_id,
                "method": "explicit",
                "error": f"Target {explicit_target_id} not found",
                "selected_target": None,
                "target_id": None,
                "ambiguous": False,
            }

        if point:
            return await TargetSelectionWorkflow._select_by_point(
                workflow_id, point, detected_targets, asset_id, project_id, user_id
            )

        if bbox:
            return await TargetSelectionWorkflow._select_by_bbox(
                workflow_id, bbox, detected_targets, asset_id, project_id, user_id
            )

        return await TargetSelectionWorkflow._select_by_prompt(
            workflow_id, prompt, detected_targets, asset_id, project_id, user_id
        )

    @staticmethod
    async def _select_by_point(
        workflow_id: str,
        point: Dict[str, float],
        detected_targets: List[Dict[str, Any]],
        asset_id: str,
        project_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        x, y = point.get("x", 0), point.get("y", 0)
        best = None
        best_dist = float("inf")
        for target in detected_targets:
            bbox = target.get("bbox") or {}
            tx = bbox.get("x", 0)
            ty = bbox.get("y", 0)
            tw = bbox.get("width", 0)
            th = bbox.get("height", 0)
            cx, cy = tx + tw / 2, ty + th / 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = target
        if best:
            return {
                "workflow_id": workflow_id,
                "method": "point",
                "selected_target": best,
                "target_id": best.get("target_id"),
                "confidence": best.get("confidence", 0.5),
                "ambiguous": False,
                "alternatives": [],
            }
        return {
            "workflow_id": workflow_id,
            "method": "point",
            "error": "No target found at point",
            "selected_target": None,
            "target_id": None,
            "ambiguous": False,
        }

    @staticmethod
    async def _select_by_bbox(
        workflow_id: str,
        bbox: Dict[str, Any],
        detected_targets: List[Dict[str, Any]],
        asset_id: str,
        project_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        best = None
        best_iou = 0.0
        for target in detected_targets:
            target_bbox = target.get("bbox") or {}
            iou = TargetSelectionWorkflow._compute_iou(bbox, target_bbox)
            if iou > best_iou:
                best_iou = iou
                best = target
        if best and best_iou > 0.3:
            return {
                "workflow_id": workflow_id,
                "method": "bbox",
                "selected_target": best,
                "target_id": best.get("target_id"),
                "confidence": best_iou,
                "ambiguous": False,
                "alternatives": [],
            }
        return {
            "workflow_id": workflow_id,
            "method": "bbox",
            "error": "No target found in bounding box",
            "selected_target": None,
            "target_id": None,
            "ambiguous": False,
        }

    @staticmethod
    async def _select_by_prompt(
        workflow_id: str,
        prompt: str,
        detected_targets: List[Dict[str, Any]],
        asset_id: str,
        project_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        if not detected_targets:
            return {
                "workflow_id": workflow_id,
                "method": "prompt",
                "error": "No targets detected in video. Please upload a video with detectable objects.",
                "selected_target": None,
                "target_id": None,
                "ambiguous": False,
                "alternatives": [],
            }

        selection = await SmartTargetSelector.select_target(
            prompt=prompt,
            detected_targets=detected_targets,
            asset_id=asset_id,
            project_id=project_id,
            user_id=user_id,
        )

        if hasattr(selection, "model_dump"):
            selection = selection.model_dump()

        primary = selection.get("primary_target")
        if primary and hasattr(primary, "model_dump"):
            primary = primary.model_dump()

        matches = selection.get("matches", [])
        serialized_matches = []
        for m in matches:
            if hasattr(m, "model_dump"):
                serialized_matches.append(m.model_dump())
            else:
                serialized_matches.append(m)

        if not primary and len(serialized_matches) == 1:
            primary = serialized_matches[0]

        if not primary and not serialized_matches:
            return {
                "workflow_id": workflow_id,
                "method": "prompt",
                "error": "Could not resolve target from prompt",
                "selected_target": None,
                "target_id": None,
                "ambiguous": False,
                "alternatives": [],
            }

        return {
            "workflow_id": workflow_id,
            "method": "prompt",
            "selected_target": primary,
            "target_id": primary.get("target_id") if primary else None,
            "confidence": primary.get("confidence", 0.0) if primary else 0.0,
            "ambiguous": selection.get("requires_clarification", False),
            "alternatives": [
                {"target_id": m.get("target_id"), "label": m.get("label"), "confidence": m.get("confidence")}
                for m in serialized_matches[1:]
            ],
        }

    @staticmethod
    def _compute_iou(box1: Dict[str, Any], box2: Dict[str, Any]) -> float:
        x1 = max(box1.get("x", 0), box2.get("x", 0))
        y1 = max(box1.get("y", 0), box2.get("y", 0))
        x2 = min(
            box1.get("x", 0) + box1.get("width", 0),
            box2.get("x", 0) + box2.get("width", 0),
        )
        y2 = min(
            box1.get("y", 0) + box1.get("height", 0),
            box2.get("y", 0) + box2.get("height", 0),
        )
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = max(0, box1.get("width", 0)) * max(0, box1.get("height", 0))
        area2 = max(0, box2.get("width", 0)) * max(0, box2.get("height", 0))
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0
