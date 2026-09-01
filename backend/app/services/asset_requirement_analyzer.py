from typing import List
from app.schemas.director import IntentExtraction, ScenePlan, AssetRequirement


class AssetRequirementAnalyzer:
    def analyze(self, intent: IntentExtraction, scenes: List[ScenePlan], references: List[str]) -> List[AssetRequirement]:
        requirements = []
        seen_types = set()

        if intent.characters:
            req_type = "character"
            if req_type not in seen_types:
                requirements.append(AssetRequirement(
                    id=f"asset-{len(requirements) + 1}",
                    type=req_type,
                    role="character",
                    description="Character reference for visual consistency across shots",
                    required=True,
                    requirements=["consistent appearance", "same clothing", "same hairstyle"],
                ))
                seen_types.add(req_type)

        if intent.products:
            req_type = "product"
            if req_type not in seen_types:
                requirements.append(AssetRequirement(
                    id=f"asset-{len(requirements) + 1}",
                    type=req_type,
                    role="product",
                    description="Product reference for visual consistency",
                    required=True,
                    requirements=["same product appearance", "consistent color", "same branding"],
                ))
                seen_types.add(req_type)

        if intent.locations:
            req_type = "location"
            if req_type not in seen_types:
                requirements.append(AssetRequirement(
                    id=f"asset-{len(requirements) + 1}",
                    type=req_type,
                    role="location",
                    description="Location reference for environment consistency",
                    required=True,
                    requirements=["same environment", "consistent weather", "same time of day"],
                ))
                seen_types.add(req_type)

        if intent.style:
            req_type = "style"
            if req_type not in seen_types:
                requirements.append(AssetRequirement(
                    id=f"asset-{len(requirements) + 1}",
                    type=req_type,
                    role="style",
                    description=f"Style reference: {intent.style}",
                    required=False,
                    requirements=["consistent visual style", "matching color palette"],
                ))
                seen_types.add(req_type)

        if references:
            req_type = "reference"
            if req_type not in seen_types:
                requirements.append(AssetRequirement(
                    id=f"asset-{len(requirements) + 1}",
                    type="reference",
                    role="general",
                    description="User-provided reference assets",
                    required=False,
                    reference_asset_id=references[0] if references else None,
                    requirements=["consistent with uploaded references"],
                ))
                seen_types.add(req_type)

        return requirements
