from typing import List
from app.schemas.director import (
    IntentExtraction,
    ScenePlan,
    ShotPlan,
    CameraRequirement,
    GenerationRequirement,
)


class ShotPlanner:
    CAMERA_MOVEMENTS = [
        "static", "pan", "tilt", "dolly", "truck", "orbit", "crane",
        "tracking", "handheld", "push-in", "pull-out", "whip-pan", "aerial", "fpv"
    ]

    LENSES = ["14mm", "18mm", "24mm", "35mm", "50mm", "85mm", "135mm", "anamorphic", "macro"]

    def plan_shots(self, scene: ScenePlan, intent: IntentExtraction) -> List[ShotPlan]:
        if scene.shots and len(scene.shots) > 0:
            return self._enhance_shots(scene.shots, intent)

        num_shots = max(1, min(4, max(2, int(scene.duration_seconds / 5))))
        shot_duration = scene.duration_seconds / num_shots
        shots = []

        for i in range(num_shots):
            shot = self._create_shot(i, shot_duration, scene, intent)
            shots.append(shot)

        return shots

    def _enhance_shots(self, existing_shots: List[ShotPlan], intent: IntentExtraction) -> List[ShotPlan]:
        enhanced = []
        for shot in existing_shots:
            if not shot.camera or shot.camera.movement == "static":
                shot.camera = self._suggest_camera(shot, intent)
            if not shot.generation:
                shot.generation = self._suggest_generation(shot, intent)
            shot.status = "planned"
            enhanced.append(shot)
        return enhanced

    def _create_shot(self, order: int, duration: float, scene: ScenePlan, intent: IntentExtraction) -> ShotPlan:
        subject = intent.subject or "subject"
        environment = scene.environment or intent.locations[0] if intent.locations else None
        camera = self._suggest_camera_for_order(order, scene, intent)
        generation = self._suggest_generation_for_order(order, scene, intent)

        descriptions = {
            0: f"Opening shot of {subject}{' in ' + environment if environment else ''}",
            1: f"Medium shot of {subject}",
            2: f"Close-up or action shot of {subject}",
            3: f"Closing shot of {subject}",
        }
        description = descriptions.get(order, f"Shot {order + 1} of {subject}")

        return ShotPlan(
            id=f"{scene.id}-shot-{order + 1}",
            scene_id=scene.id,
            order=order,
            description=description,
            subject=subject,
            action=None,
            environment=environment,
            camera=camera,
            lighting="cinematic lighting",
            composition="rule of thirds",
            style=intent.style,
            motion="smooth",
            duration_seconds=duration,
            references=intent.references[:2],
            characters=intent.characters.copy(),
            products=intent.products.copy(),
            locations=intent.locations.copy(),
            audio=[],
            continuity=[],
            generation=generation,
            status="planned",
        )

    def _suggest_camera_for_order(self, order: int, scene: ScenePlan, intent: IntentExtraction) -> CameraRequirement:
        if order == 0:
            return CameraRequirement(movement="push-in", lens="35mm" if intent.content_type == "cinematic" else "50mm")
        elif order == 1:
            return CameraRequirement(movement="static", lens="85mm")
        elif order == 2:
            return CameraRequirement(movement="orbit", lens="macro" if "product" in (intent.products or []) else "50mm")
        else:
            return CameraRequirement(movement="pull-out", lens="24mm")

    def _suggest_generation_for_order(self, order: int, scene: ScenePlan, intent: IntentExtraction) -> GenerationRequirement:
        has_references = bool(intent.references or scene.references)
        if has_references and order == 0:
            method = "IMAGE_TO_VIDEO"
        elif order > 0 and has_references:
            method = "IMAGE_TO_VIDEO"
        else:
            method = "TEXT_TO_VIDEO"

        capabilities = []
        if has_references:
            capabilities.append("REFERENCE_IMAGES")
        if intent.characters:
            capabilities.append("CHARACTER_REFERENCE")
        if intent.products:
            capabilities.append("PRODUCT_REFERENCE")

        return GenerationRequirement(
            id=f"{scene.id}-shot-{order + 1}-gen",
            method=method,
            required_capabilities=capabilities,
            parameters={"seed": None, "guidance_scale": 7.5},
        )

    def _suggest_camera(self, shot: ShotPlan, intent: IntentExtraction) -> CameraRequirement:
        subject = (shot.subject or intent.subject or "").lower()
        if "macro" in subject or "product" in (intent.products or []):
            return CameraRequirement(movement="push-in", lens="macro")
        if "person" in (intent.characters or []):
            return CameraRequirement(movement="static", lens="85mm")
        return CameraRequirement(movement="static", lens="50mm")

    def _suggest_generation(self, shot: ShotPlan, intent: IntentExtraction) -> GenerationRequirement:
        has_references = bool(shot.references or intent.references)
        method = "IMAGE_TO_VIDEO" if has_references else "TEXT_TO_VIDEO"
        capabilities = ["REFERENCE_IMAGES"] if has_references else []
        return GenerationRequirement(
            id=f"{shot.id}-gen",
            method=method,
            required_capabilities=capabilities,
            parameters={"seed": None, "guidance_scale": 7.5},
        )
