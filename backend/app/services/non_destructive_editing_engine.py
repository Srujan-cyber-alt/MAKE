"""
Non-Destructive Editing Engine for MAKE AI Video Phase 17.

All editing operations are non-destructive.
Original assets are never modified.
Edits are represented as operations, transforms, effects, metadata, and versions.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EditOperationType(str, Enum):
    TRIM = "trim"
    SPLIT = "split"
    CUT = "cut"
    CROP = "crop"
    DUPLICATE = "duplicate"
    MOVE = "move"
    REORDER = "reorder"
    REPLACE = "replace"
    FREEZE_FRAME = "freeze_frame"
    HOLD_FRAME = "hold_frame"
    REVERSE = "reverse"
    SPEED_CHANGE = "speed_change"
    TRANSITION = "transition"
    EFFECT = "effect"
    COLOR = "color"
    AUDIO = "audio"
    MASK = "mask"
    KEYFRAME = "keyframe"
    GROUP = "group"
    UNGROUP = "ungroup"
    LINK = "link"
    UNLINK = "unlink"


@dataclass
class EditOperation:
    operation_id: str
    operation_type: EditOperationType
    target_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EditPlan:
    plan_id: str
    project_id: str
    operations: List[EditOperation] = field(default_factory=list)
    description: str = ""
    status: str = "draft"
    metadata: Dict[str, Any] = field(default_factory=dict)


class NonDestructiveEditingEngine:
    def __init__(self):
        self._edit_plans: Dict[str, EditPlan] = {}

    def create_operation(self, operation_type: EditOperationType, target_id: str, parameters: Dict[str, Any] = None, user_id: str = None) -> EditOperation:
        import uuid
        return EditOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            target_id=target_id,
            parameters=parameters or {},
            user_id=user_id,
        )

    def create_edit_plan(self, project_id: str, description: str = "") -> EditPlan:
        import uuid
        plan = EditPlan(
            plan_id=str(uuid.uuid4()),
            project_id=project_id,
            description=description,
        )
        self._edit_plans[plan.plan_id] = plan
        return plan

    def add_operation_to_plan(self, plan_id: str, operation: EditOperation) -> bool:
        plan = self._edit_plans.get(plan_id)
        if not plan:
            return False
        plan.operations.append(operation)
        return True

    def get_edit_plan(self, plan_id: str) -> Optional[EditPlan]:
        return self._edit_plans.get(plan_id)

    def apply_edit_plan(self, plan_id: str, timeline: Dict) -> List[Dict[str, Any]]:
        plan = self._edit_plans.get(plan_id)
        if not plan:
            return []
        applied = []
        for op in plan.operations:
            result = self._apply_operation(timeline, op)
            applied.append(result)
        plan.status = "applied"
        return applied

    def _apply_operation(self, timeline: Dict, operation: EditOperation) -> Dict[str, Any]:
        return {
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type.value,
            "target_id": operation.target_id,
            "status": "applied",
            "parameters": operation.parameters,
        }

    def validate_operation(self, operation: EditOperation, timeline: Dict) -> Dict[str, Any]:
        errors = []
        target_found = False
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == operation.target_id:
                    target_found = True
                    if clip.get("locked"):
                        errors.append(f"Target {operation.target_id} is locked")
        if not target_found:
            errors.append(f"Target {operation.target_id} not found")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "operation_id": operation.operation_id,
        }


non_destructive_editing_engine = NonDestructiveEditingEngine()
