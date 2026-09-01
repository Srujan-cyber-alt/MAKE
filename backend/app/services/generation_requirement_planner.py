from typing import List
from app.schemas.director import ScenePlan, ShotPlan, IntentExtraction, GenerationRequirement


class GenerationRequirementPlanner:
    METHODS = ["TEXT_TO_VIDEO", "IMAGE_TO_VIDEO", "VIDEO_TO_VIDEO", "REFERENCE_GENERATION", "GENERATIVE_TRANSFORMATION"]
    CAPABILITIES = [
        "REFERENCE_IMAGES", "VIDEO_TO_VIDEO", "IMAGE_TO_VIDEO", "CAMERA_CONTROL",
        "CHARACTER_REFERENCE", "PRODUCT_REFERENCE", "MOTION_REFERENCE", "START_END_FRAME"
    ]

    def plan_generation(self, scenes: List[ScenePlan], intent: IntentExtraction) -> List[GenerationRequirement]:
        requirements = []
        seen_methods = set()

        for scene in scenes:
            for shot in scene.shots:
                if shot.generation:
                    method = shot.generation.method
                    if method not in seen_methods:
                        requirements.append(GenerationRequirement(
                            id=f"generation-{len(requirements) + 1}",
                            method=method,
                            required_capabilities=shot.generation.required_capabilities,
                            parameters=shot.generation.parameters,
                        ))
                        seen_methods.add(method)

        if not requirements:
            requirements.append(GenerationRequirement(
                id="generation-1",
                method="TEXT_TO_VIDEO",
                required_capabilities=[],
                parameters={"guidance_scale": 7.5, "seed": None},
            ))

        return requirements
