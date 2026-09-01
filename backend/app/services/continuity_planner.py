from typing import List
from app.schemas.director import ScenePlan, ContinuityRequirement


class ContinuityPlanner:
    def plan_continuity(self, scenes: List[ScenePlan]) -> List[ContinuityRequirement]:
        requirements = []

        for scene in scenes:
            if scene.characters:
                requirements.append(ContinuityRequirement(
                    id=f"continuity-{len(requirements) + 1}",
                    type="character",
                    description=f"Maintain character consistency in {scene.title}",
                    applies_to=[shot.id for shot in scene.shots],
                    rules=["same person", "same clothing", "same hairstyle"],
                ))

            if scene.products:
                requirements.append(ContinuityRequirement(
                    id=f"continuity-{len(requirements) + 1}",
                    type="product",
                    description=f"Maintain product consistency in {scene.title}",
                    applies_to=[shot.id for shot in scene.shots],
                    rules=["same product", "same color", "same design", "same branding"],
                ))

            if scene.locations:
                requirements.append(ContinuityRequirement(
                    id=f"continuity-{len(requirements) + 1}",
                    type="location",
                    description=f"Maintain environment consistency in {scene.title}",
                    applies_to=[shot.id for shot in scene.shots],
                    rules=["same environment", "same weather", "same time of day"],
                ))

            requirements.append(ContinuityRequirement(
                id=f"continuity-{len(requirements) + 1}",
                type="lighting",
                description=f"Maintain lighting consistency in {scene.title}",
                applies_to=[shot.id for shot in scene.shots],
                rules=["consistent lighting direction", "matching color temperature"],
            ))

        return requirements
