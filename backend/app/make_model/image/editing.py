"""MAKE Image Engine — Editing Engine.

Non-destructive semantic editing with Intent Brush.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class EditOperation:
    operation_id: str
    op_type: str
    target: str
    params: Dict[str, Any] = field(default_factory=dict)
    mask: Optional[np.ndarray] = None
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "op_type": self.op_type,
            "target": self.target,
            "params": dict(self.params),
            "has_mask": self.mask is not None,
            "order": self.order,
        }


@dataclass
class IntentBrush:
    operation_queue: List[EditOperation] = field(default_factory=list)

    def add(self, op: EditOperation) -> None:
        self.operation_queue.append(op)
        self.operation_queue.sort(key=lambda x: x.order)

    def pop(self) -> Optional[EditOperation]:
        if self.operation_queue:
            return self.operation_queue.pop(0)
        return None

    def clear(self) -> None:
        self.operation_queue = []


class EditingEngine:
    def __init__(self):
        self.brush = IntentBrush()
        self.supported_ops = [
            "inpaint", "outpaint", "replace_object", "remove_object",
            "replace_background", "lighting_change", "material_change",
            "expression_change", "pose_change", "camera_change",
            "environment_change", "weather_change", "time_change",
            "style_change", "composition_change",
        ]

    def apply(self, world: Any, operation: EditOperation) -> Any:
        import copy
        new_world = copy.deepcopy(world)
        params = operation.params
        if operation.op_type == "lighting_change" and hasattr(new_world, "lighting"):
            new_world.lighting.key_intensity = params.get("key_intensity", new_world.lighting.key_intensity)
            new_world.lighting.key_color = tuple(params.get("key_color", new_world.lighting.key_color))
        elif operation.op_type == "material_change" and hasattr(new_world, "material"):
            new_world.material.base_color = tuple(params.get("base_color", new_world.material.base_color))
            new_world.material.metallic = params.get("metallic", new_world.material.metallic)
        elif operation.op_type == "time_change" and hasattr(new_world, "lighting"):
            new_world.lighting.key_intensity = params.get("intensity", new_world.lighting.key_intensity)
        return new_world

    def create_operation(self, op_type: str, target: str, params: Dict[str, Any], mask: Optional[np.ndarray] = None) -> EditOperation:
        return EditOperation(
            operation_id=f"{op_type}_{target}",
            op_type=op_type,
            target=target,
            params=params,
            mask=mask,
            order=len(self.brush.operation_queue),
        )


__all__ = [
    "EditOperation",
    "IntentBrush",
    "EditingEngine",
]
