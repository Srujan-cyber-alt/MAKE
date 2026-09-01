from typing import Optional, List, Dict, Any
from app.schemas.director import ShotPlan, IntentExtraction


class PromptCompiler:
    def compile(
        self,
        shot: ShotPlan,
        intent: IntentExtraction,
        negative_constraints: List[str] = None,
    ) -> str:
        parts = []

        if shot.subject:
            parts.append(f"SUBJECT: {shot.subject}")

        if shot.action:
            parts.append(f"ACTION: {shot.action}")

        if shot.environment:
            parts.append(f"ENVIRONMENT: {shot.environment}")

        if shot.camera:
            camera_parts = []
            if shot.camera.movement and shot.camera.movement != "static":
                camera_parts.append(shot.camera.movement)
            if shot.camera.lens:
                camera_parts.append(shot.camera.lens)
            if camera_parts:
                parts.append(f"CAMERA: {' '.join(camera_parts)}")

        if shot.lighting:
            parts.append(f"LIGHTING: {shot.lighting}")

        if shot.composition:
            parts.append(f"COMPOSITION: {shot.composition}")

        if shot.style or intent.style:
            parts.append(f"STYLE: {shot.style or intent.style}")

        if shot.motion:
            parts.append(f"MOTION: {shot.motion}")

        if intent.tone:
            parts.append(f"TONE: {intent.tone}")

        if shot.continuity:
            continuity = ", ".join(shot.continuity)
            parts.append(f"CONTINUITY: {continuity}")

        if shot.references:
            parts.append(f"REFERENCES: {', '.join(shot.references)}")

        if negative_constraints:
            parts.append(f"NEGATIVE: {', '.join(negative_constraints)}")

        return "\n".join(parts)

    def compile_provider_prompt(self, shot: ShotPlan, intent: IntentExtraction, provider: str = None) -> str:
        base_prompt = self.compile(shot, intent)
        provider_prefix = {
            "runway": "Cinematic video, ",
            "pika": "High quality video, ",
            "test": "Test video, ",
        }.get(provider, "")

        return f"{provider_prefix}{base_prompt}" if provider_prefix else base_prompt

    def extract_negative_prompt(self, shot: ShotPlan, intent: IntentExtraction) -> str:
        negatives = []
        if intent.content_type == "commercial":
            negatives.extend(["blurry", "low quality", "distorted"])
        if intent.tone == "premium":
            negatives.extend(["cheap looking", "amateur", "pixelated"])
        if shot.camera and shot.camera.movement in ["handheld"]:
            negatives.extend(["too stable", "robotic"])

        return ", ".join(negatives) if negatives else "blurry, low quality, distorted"
