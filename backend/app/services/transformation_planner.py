from typing import List, Dict, Any, Optional
from app.schemas.transformation import (
    TransformationOperation,
    TransformationPlan,
    TransformationType,
)
from app.providers.registry import get_provider_registry
from app.providers.base import ProviderCapability
from app.services.transformation_analyzer import TransformationAnalyzer


class TransformationPlanner:

    @staticmethod
    def create_plan(
        project_id: str,
        source_asset_id: str,
        operations: List[TransformationOperation],
        preferences: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        preferences = preferences or {}
        ordered_ops = TransformationPlanner._order_operations(operations)
        validated_ops, errors = TransformationPlanner._validate_capabilities(ordered_ops)
        dependencies = TransformationPlanner._build_dependencies(validated_ops)
        capability_issues = TransformationPlanner._check_capabilities(validated_ops)

        if capability_issues:
            errors.extend(capability_issues)

        plan = {
            "project_id": project_id,
            "source_asset_id": source_asset_id,
            "operations": [op.model_dump() for op in validated_ops],
            "dependencies": dependencies,
            "references": list(set(ref for op in validated_ops for ref in op.references)),
            "temporal_constraints": {
                "preserve_audio": preferences.get("preserve_audio", True),
                "maintain_duration": preferences.get("maintain_duration", True),
                "frame_rate": preferences.get("frame_rate", "source"),
            },
            "identity_constraints": {
                "lock_identity": preferences.get("preserve_identity", True),
                "lock_product": preferences.get("preserve_product", True),
                "reference_images": preferences.get("reference_asset_ids", []),
            },
            "output_requirements": {
                "resolution": preferences.get("resolution", "source"),
                "aspect_ratio": preferences.get("aspect_ratio", "source"),
                "format": preferences.get("format", "mp4"),
                "codec": preferences.get("codec", "h264"),
            },
            "status": "ready" if not errors else "blocked",
            "errors": errors,
            "warnings": TransformationPlanner._generate_warnings(validated_ops),
        }
        return plan

    @staticmethod
    def _order_operations(operations: List[TransformationOperation]) -> List[TransformationOperation]:
        priority = {
            TransformationType.OBJECT_REMOVAL: 1,
            TransformationType.INPAINTING: 2,
            TransformationType.OUTPAINTING: 2,
            TransformationType.BACKGROUND_REPLACEMENT: 3,
            TransformationType.OBJECT_REPLACEMENT: 4,
            TransformationType.ENVIRONMENT_TRANSFORM: 5,
            TransformationType.LIGHTING_TRANSFORM: 6,
            TransformationType.WEATHER_TRANSFORM: 7,
            TransformationType.STYLE_TRANSFER: 8,
            TransformationType.VIDEO_TO_VIDEO: 8,
            TransformationType.ACTION_TRANSFORM: 9,
            TransformationType.MOTION_TRANSFER: 9,
            TransformationType.CAMERA_TRANSFORM: 10,
            TransformationType.VFX_APPLY: 11,
            TransformationType.IDENTITY_PRESERVE: 0,
        }
        return sorted(operations, key=lambda op: priority.get(op.type, 5))

    @staticmethod
    def _validate_capabilities(operations: List[TransformationOperation]) -> tuple[List[TransformationOperation], List[str]]:
        validated = []
        errors = []
        registry = get_provider_registry()
        available_capabilities = set()
        for provider in registry.get_all().values():
            available_capabilities.update(c.value for c in provider.get_capabilities())

        for op in operations:
            required = TransformationAnalyzer._required_capabilities(op.type)
            missing = [c for c in required if c not in available_capabilities]
            if missing:
                errors.append(
                    f"Operation '{op.type.value}' requires capabilities {missing} which are not available from any provider."
                )
            else:
                validated.append(op)
        return validated, errors

    @staticmethod
    def _build_dependencies(operations: List[TransformationOperation]) -> Dict[str, List[str]]:
        deps: Dict[str, List[str]] = {}
        for i, op in enumerate(operations):
            op_id = f"op-{i}"
            if op.dependencies:
                deps[op_id] = op.dependencies
            if i > 0:
                prev_op_id = f"op-{i-1}"
                if op_id not in deps:
                    deps[op_id] = [prev_op_id]
                else:
                    if prev_op_id not in deps[op_id]:
                        deps[op_id].append(prev_op_id)
        return deps

    @staticmethod
    def _check_capabilities(operations: List[TransformationOperation]) -> List[str]:
        issues = []
        has_v2v = any(op.type == TransformationType.VIDEO_TO_VIDEO for op in operations)
        has_removal = any(op.type == TransformationType.OBJECT_REMOVAL for op in operations)
        has_replacement = any(op.type == TransformationType.OBJECT_REPLACEMENT for op in operations)

        if has_v2v:
            issues.append("VIDEO_TO_VIDEO requires a provider with video transformation capabilities.")
        if has_removal:
            issues.append("OBJECT_REMOVAL requires inpainting and segmentation capabilities.")
        if has_replacement:
            issues.append("OBJECT_REPLACEMENT requires reference image support and compositing capabilities.")

        return issues

    @staticmethod
    def _generate_warnings(operations: List[TransformationOperation]) -> List[str]:
        warnings = []
        identity_ops = [op for op in operations if op.preserve_identity]
        if identity_ops and len(operations) > 1:
            warnings.append("Identity preservation requested across multiple operations. Consistency cannot be guaranteed.")

        for op in operations:
            if op.strength < 0.3:
                warnings.append(f"Operation '{op.type.value}' has low strength ({op.strength}). Result may be subtle.")
            elif op.strength > 0.9:
                warnings.append(f"Operation '{op.type.value}' has high strength ({op.strength}). May introduce artifacts.")

        return warnings
