from typing import List
from app.schemas.director import IntentExtraction, ScenePlan, ShotPlan, CameraRequirement


class ScenePlanner:
    def plan_scenes(self, intent: IntentExtraction, references: List[str]) -> List[ScenePlan]:
        duration = intent.total_duration_seconds
        scenes = []

        if intent.content_type in ("commercial", "advertisement"):
            scenes = self._plan_commercial_scenes(intent, duration)
        elif intent.content_type == "social":
            scenes = self._plan_social_scenes(intent, duration)
        elif intent.content_type == "cinematic":
            scenes = self._plan_cinematic_scenes(intent, duration)
        elif intent.content_type in ("storytelling", "documentary"):
            scenes = self._plan_narrative_scenes(intent, duration)
        else:
            scenes = self._plan_default_scenes(intent, duration)

        total = sum(s.duration_seconds for s in scenes)
        if total > 0 and abs(total - duration) > duration * 0.15:
            for scene in scenes:
                scene.duration_seconds = duration / len(scenes)

        return scenes

    def _plan_commercial_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        num_scenes = max(2, min(4, max(2, duration // 8)))

        if num_scenes == 2:
            scenes.append(self._create_scene(0, "Product Introduction", "Show the product clearly and establish its identity", duration * 0.4, intent))
            scenes.append(self._create_scene(1, "Product in Action", "Demonstrate the product in use or environment", duration * 0.6, intent))
        elif num_scenes == 3:
            scenes.append(self._create_scene(0, "Hook", "Grab attention with a compelling visual", duration * 0.25, intent))
            scenes.append(self._create_scene(1, "Demonstration", "Showcase key product features and benefits", duration * 0.45, intent))
            scenes.append(self._create_scene(2, "Call to Action", "End with the product hero shot and brand message", duration * 0.3, intent))
        else:
            scenes.append(self._create_scene(0, "Hook", "Grab attention with the product", duration * 0.2, intent))
            scenes.append(self._create_scene(1, "Feature 1", "Show a key product feature", duration * 0.25, intent))
            scenes.append(self._create_scene(2, "Feature 2", "Show another product feature", duration * 0.25, intent))
            scenes.append(self._create_scene(3, "Call to Action", "Hero product shot and CTA", duration * 0.3, intent))

        return scenes

    def _plan_social_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        scenes.append(self._create_scene(0, "Hook", "Quick attention-grabbing opening", duration * 0.3, intent))
        scenes.append(self._create_scene(1, "Content", "Main content and engagement", duration * 0.5, intent))
        scenes.append(self._create_scene(2, "CTA", "Call to action or closing", duration * 0.2, intent))
        return scenes

    def _plan_cinematic_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        num_scenes = max(2, min(5, duration // 10))
        scene_duration = duration / num_scenes

        for i in range(num_scenes):
            if i == 0:
                purpose = "Establishing shot"
                name = "Opening"
            elif i == num_scenes - 1:
                purpose = "Conclusion"
                name = "Closing"
            else:
                purpose = f"Scene {i + 1}"
                name = f"Scene {i + 1}"
            scenes.append(self._create_scene(i, name, purpose, scene_duration, intent))

        return scenes

    def _plan_narrative_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        num_scenes = max(2, min(4, duration // 10))
        scene_duration = duration / num_scenes

        for i in range(num_scenes):
            if i == 0:
                name = "Introduction"
                purpose = "Introduce the subject and setting"
            elif i == num_scenes - 1:
                name = "Conclusion"
                purpose = "Conclude the narrative"
            else:
                name = f"Development {i}"
                purpose = f"Advance the story"
            scenes.append(self._create_scene(i, name, purpose, scene_duration, intent))

        return scenes

    def _plan_default_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        scenes.append(self._create_scene(0, "Opening", "Introduction and setup", duration * 0.5, intent))
        scenes.append(self._create_scene(1, "Main", "Main content", duration * 0.5, intent))
        return scenes

    def _create_scene(self, order: int, name: str, purpose: str, duration: float, intent: IntentExtraction) -> ScenePlan:
        num_shots = max(1, min(4, max(2, int(duration / 5))))
        shots = []
        scene_id = f"scene-{order + 1}"

        for i in range(num_shots):
            shot = self._create_shot(i, duration / num_shots, intent, scene_id)
            shots.append(shot)

        return ScenePlan(
            id=scene_id,
            order=order,
            title=name,
            purpose=purpose,
            description=purpose,
            environment=intent.locations[0] if intent.locations else None,
            duration_seconds=duration,
            shots=shots,
            references=intent.references[:2],
            characters=intent.characters.copy(),
            products=intent.products.copy(),
            locations=intent.locations.copy(),
            continuity=[],
        )

    def _create_shot(self, order: int, duration: float, intent: IntentExtraction, scene_id: str = "") -> ShotPlan:
        subject = intent.subject or "subject"
        environment = intent.locations[0] if intent.locations else None

        if order == 0:
            description = f"Opening shot of {subject}"
            camera = CameraRequirement(movement="push-in", lens="50mm")
        elif order == 1:
            description = f"Medium shot showing {subject} details"
            camera = CameraRequirement(movement="static", lens="85mm")
        elif order == 2:
            description = f"Close-up or action shot of {subject}"
            camera = CameraRequirement(movement="orbit", lens="macro")
        else:
            description = f"Closing shot of {subject}"
            camera = CameraRequirement(movement="pull-out", lens="35mm")

        shot_id = f"{scene_id}-shot-{order + 1}" if scene_id else f"shot-{order + 1}"

        return ShotPlan(
            id=shot_id,
            scene_id=scene_id,
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
            generation=None,
            status="planned",
        )
