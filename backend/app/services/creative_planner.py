from typing import Optional
from app.schemas.director import IntentExtraction


class CreativePlanner:
    def create_concept(self, intent: IntentExtraction) -> dict:
        content_descriptions = {
            "commercial": "a compelling product advertisement",
            "advertisement": "a compelling product advertisement",
            "cinematic": "a cinematic visual experience",
            "social": "an engaging social media video",
            "music_video": "a dynamic music video",
            "explainer": "a clear and informative explainer",
            "trailer": "an exciting promotional trailer",
            "ugc": "an authentic user-generated style video",
            "documentary": "a documentary-style piece",
            "storytelling": "a narrative-driven story",
        }

        description = content_descriptions.get(intent.content_type, "a creative video")
        tone_desc = f"with a {intent.tone} tone" if intent.tone else ""
        style_desc = f"in a {intent.style} style" if intent.style else ""
        platform_desc = f"optimized for {intent.platform}" if intent.platform else ""

        concept_parts = [f"Create {description}"]
        if tone_desc:
            concept_parts.append(tone_desc)
        if style_desc:
            concept_parts.append(style_desc)
        if platform_desc:
            concept_parts.append(platform_desc)

        concept = " ".join(concept_parts)

        title = self._generate_title(intent)
        objective = self._generate_objective(intent)

        return {
            "title": title,
            "concept": concept,
            "objective": objective,
        }

    def _generate_title(self, intent: IntentExtraction) -> str:
        parts = []
        if intent.content_type:
            parts.append(intent.content_type.replace("_", " ").title())
        if intent.subject:
            parts.append(intent.subject.title())
        if intent.platform:
            parts.append(f"for {intent.platform.title()}")
        return " ".join(parts) if parts else "Video Project"

    def _generate_objective(self, intent: IntentExtraction) -> str:
        objective = intent.story or intent.objective or "Create a video"
        if len(objective) > 200:
            objective = objective[:197] + "..."
        return objective
