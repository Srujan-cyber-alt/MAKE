from typing import List
from app.schemas.director import IntentExtraction, ScenePlan, AudioRequirement


class AudioPlanner:
    def plan_audio(self, intent: IntentExtraction, scenes: List[ScenePlan]) -> List[AudioRequirement]:
        requirements = []
        total_duration = sum(scene.duration_seconds for scene in scenes)

        if intent.voiceover:
            requirements.append(AudioRequirement(
                id="audio-voiceover",
                type="voiceover",
                description="Voiceover narration",
                duration_seconds=total_duration,
                parameters={"tone": intent.tone, "script": None},
            ))

        if intent.music:
            requirements.append(AudioRequirement(
                id="audio-music",
                type="music",
                description="Background music",
                duration_seconds=total_duration,
                parameters={"style": intent.style or "cinematic", "mood": intent.tone},
            ))

        audio_types = intent.audio or {}
        if audio_types.get("sfx"):
            requirements.append(AudioRequirement(
                id="audio-sfx",
                type="sfx",
                description="Sound effects",
                duration_seconds=total_duration,
                parameters={"style": "cinematic"},
            ))

        if audio_types.get("ambient"):
            requirements.append(AudioRequirement(
                id="audio-ambient",
                type="ambient",
                description="Ambient sound",
                duration_seconds=total_duration,
                parameters={"environment": intent.locations[0] if intent.locations else "studio"},
            ))

        if intent.captions:
            requirements.append(AudioRequirement(
                id="audio-captions",
                type="captions",
                description="On-screen captions",
                duration_seconds=total_duration,
                parameters={"style": "modern"},
            ))

        return requirements
