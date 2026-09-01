from typing import List, Optional
from app.schemas.director import DirectorPlan, ScenePlan, ShotPlan, ExportRequirement


class DirectorValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DirectorPlanValidator:
    @staticmethod
    def validate(plan: DirectorPlan) -> List[str]:
        errors = []
        errors.extend(DirectorPlanValidator._validate_plan_structure(plan))
        errors.extend(DirectorPlanValidator._validate_scenes(plan.scenes))
        errors.extend(DirectorPlanValidator._validate_duration(plan))
        errors.extend(DirectorPlanValidator._validate_export(plan.export_requirements))
        errors.extend(DirectorPlanValidator._validate_assets(plan.asset_requirements))
        return errors

    @staticmethod
    def _validate_plan_structure(plan: DirectorPlan) -> List[str]:
        errors = []
        if not plan.id:
            errors.append("Plan must have a valid ID")
        if not plan.project_id:
            errors.append("Plan must have a valid project_id")
        if not plan.scenes or len(plan.scenes) == 0:
            errors.append("Plan must have at least one scene")
        return errors

    @staticmethod
    def _validate_scenes(scenes: List[ScenePlan]) -> List[str]:
        errors = []
        if not scenes:
            errors.append("Plan must contain scenes")
            return errors

        for scene in scenes:
            if not scene.shots or len(scene.shots) == 0:
                errors.append(f"Scene '{scene.name}' must have at least one shot")
            for shot in scene.shots:
                if shot.duration_seconds <= 0:
                    errors.append(f"Shot {shot.id} must have positive duration")
                if shot.order < 0:
                    errors.append(f"Shot {shot.id} must have non-negative order")

        return errors

    @staticmethod
    def _validate_duration(plan: DirectorPlan) -> List[str]:
        errors = []
        total_duration = sum(s.duration_seconds for s in plan.scenes)
        expected_duration = plan.intent.total_duration_seconds

        if total_duration <= 0:
            errors.append("Total plan duration must be positive")
        elif abs(total_duration - expected_duration) > expected_duration * 0.2:
            errors.append(
                f"Total duration {total_duration}s deviates more than 20% from intended {expected_duration}s"
            )

        return errors

    @staticmethod
    def _validate_export(export_req: ExportRequirement) -> List[str]:
        errors = []
        valid_ratios = ["16:9", "9:16", "1:1", "4:5", "4:3"]
        if export_req.aspect_ratio not in valid_ratios:
            errors.append(f"Unsupported aspect ratio: {export_req.aspect_ratio}")

        if export_req.fps <= 0 or export_req.fps > 120:
            errors.append(f"Invalid FPS: {export_req.fps}")

        if export_req.duration_seconds <= 0:
            errors.append("Export duration must be positive")

        return errors

    @staticmethod
    def _validate_assets(asset_requirements: List) -> List[str]:
        errors = []
        for asset in asset_requirements:
            if not asset.id:
                errors.append("Asset requirement must have an ID")
            if not asset.type:
                errors.append(f"Asset requirement {asset.id} must have a type")
        return errors

    @staticmethod
    def is_valid(plan: DirectorPlan) -> bool:
        return len(DirectorPlanValidator.validate(plan)) == 0
