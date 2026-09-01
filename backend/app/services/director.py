import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.director import (
    IntentExtraction,
    ScenePlan,
    ShotPlan,
    AssetRequirement,
    ContinuityRequirement,
    GenerationRequirement,
    AudioRequirement,
    ExportRequirement,
    DirectorPlan,
    DirectorRequest,
    CameraRequirement,
)
from app.models.models import Project, DirectorPlan as DirectorPlanModel
from app.core.database import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession


class DirectorService:
    def __init__(self):
        self.camera_movements = [
            "static", "pan", "tilt", "dolly", "truck", "orbit", "crane",
            "tracking", "handheld", "push-in", "pull-out", "whip-pan", "aerial", "fpv"
        ]
        self.lenses = ["14mm", "18mm", "24mm", "35mm", "50mm", "85mm", "135mm", "anamorphic"]
        self.content_types = {
            "commercial": ["commercial", "ad", "advertisement", "product", "brand", "promotion"],
            "cinematic": ["cinematic", "film", "movie", "scene", "short"],
            "social": ["social", "tiktok", "reel", "short", "viral", "story"],
            "music_video": ["music", "mv", "video"],
            "explainer": ["explainer", "tutorial", "how to", "guide"],
            "trailer": ["trailer", "teaser", "promo"],
            "ugc": ["ugc", "user generated", "authentic", "natural"],
            "documentary": ["documentary", "real", "interview", "footage"],
        }
        self.platforms = {
            "youtube": ["youtube", "yt"],
            "instagram": ["instagram", "ig", "reel"],
            "tiktok": ["tiktok", "tk"],
            "twitter": ["twitter", "x"],
            "linkedin": ["linkedin"],
            "facebook": ["facebook", "fb"],
        }

    async def create_plan(self, request: DirectorRequest, project_id: Optional[str] = None) -> DirectorPlan:
        intent = self._extract_intent(request.prompt, request.preferences, request.references)
        scenes = self._plan_scenes(intent, request.references)
        asset_requirements = self._extract_asset_requirements(intent, scenes, request.references)
        continuity_requirements = self._extract_continuity_requirements(scenes)
        audio_requirements = self._extract_audio_requirements(intent, scenes)
        export_requirements = self._extract_export_requirements(intent)

        plan = DirectorPlan(
            id=str(uuid.uuid4()),
            project_id=project_id or "",
            intent=intent,
            scenes=scenes,
            asset_requirements=asset_requirements,
            continuity_requirements=continuity_requirements,
            audio_requirements=audio_requirements,
            export_requirements=export_requirements,
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return plan

    def _extract_intent(self, prompt: str, preferences: Dict[str, Any], references: List[str] = None) -> IntentExtraction:
        prompt_lower = prompt.lower()
        if references is None:
            references = []

        content_type = self._detect_content_type(prompt_lower)
        tone = self._detect_tone(prompt_lower)
        style = self._detect_style(prompt_lower)
        platform = self._detect_platform(prompt_lower)
        duration = self._extract_duration(prompt)
        aspect_ratio = self._extract_aspect_ratio(prompt_lower, platform)
        resolution = preferences.get("resolution", "1080p")
        subject = self._extract_subject(prompt)
        audience = self._extract_audience(prompt_lower)
        characters = self._extract_characters(prompt)
        products = self._extract_products(prompt)
        locations = self._extract_locations(prompt)
        audio = self._extract_audio(prompt_lower)
        voiceover = bool(re.search(r'\b(voiceover|voice over|narrator|narrated)\b', prompt_lower))
        music = bool(re.search(r'\b(music|soundtrack|score|bgm)\b', prompt_lower))
        captions = bool(re.search(r'\b(caption|subtitle|text)\b', prompt_lower))
        cta = self._extract_cta(prompt)

        return IntentExtraction(
            objective=prompt[:200],
            content_type=content_type,
            subject=subject,
            audience=audience,
            tone=tone,
            style=style,
            story=prompt,
            total_duration_seconds=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            platform=platform,
            references=references,
            characters=characters,
            products=products,
            locations=locations,
            audio=audio,
            voiceover=voiceover,
            music=music,
            captions=captions,
            cta=cta,
        )

    def _detect_content_type(self, prompt: str) -> str:
        for ctype, keywords in self.content_types.items():
            if any(kw in prompt for kw in keywords):
                return ctype
        return "cinematic"

    def _detect_tone(self, prompt: str) -> str:
        if any(w in prompt for w in ["luxury", "premium", "elegant", "sophisticated"]):
            return "premium"
        if any(w in prompt for w in ["fun", "energetic", "vibrant", "playful"]):
            return "energetic"
        if any(w in prompt for w in ["professional", "corporate", "business"]):
            return "professional"
        if any(w in prompt for w in ["dramatic", "intense", "dark"]):
            return "dramatic"
        return "professional"

    def _detect_style(self, prompt: str) -> Optional[str]:
        styles = {
            "cinematic": ["cinematic", "film", "movie-like"],
            "minimalist": ["minimalist", "clean", "simple"],
            "vintage": ["vintage", "retro", "old-school"],
            "futuristic": ["futuristic", "sci-fi", "cyberpunk"],
            "documentary": ["documentary", "realistic", "raw"],
            "animation": ["animated", "animation", "cartoon"],
        }
        for style, keywords in styles.items():
            if any(kw in prompt for kw in keywords):
                return style
        return None

    def _detect_platform(self, prompt: str) -> Optional[str]:
        for platform, keywords in self.platforms.items():
            if any(kw in prompt for kw in keywords):
                return platform
        return None

    def _extract_duration(self, prompt: str) -> int:
        match = re.search(r'(\d+)\s*(?:second|sec|s)', prompt, re.IGNORECASE)
        if match:
            duration = int(match.group(1))
            if duration < 5:
                return 5
            if duration > 120:
                return 120
            return duration
        return 30

    def _extract_aspect_ratio(self, prompt: str, platform: Optional[str]) -> str:
        if "vertical" in prompt or "9:16" in prompt or platform in ["tiktok", "instagram"]:
            return "9:16"
        if "square" in prompt or "1:1" in prompt or platform == "instagram":
            return "1:1"
        if "wide" in prompt or "16:9" in prompt or platform == "youtube":
            return "16:9"
        return "16:9"

    def _extract_subject(self, prompt: str) -> Optional[str]:
        subjects = ["watch", "product", "person", "car", "dog", "cat", "building", "city", "nature"]
        for subj in subjects:
            if subj in prompt.lower():
                return subj
        return None

    def _extract_audience(self, prompt: str) -> Optional[str]:
        audiences = ["consumer", "business", "enterprise", "young", "adult", "luxury", "mass market"]
        for aud in audiences:
            if aud in prompt:
                return aud
        return None

    def _extract_characters(self, prompt: str) -> List[str]:
        characters = []
        if re.search(r'\b(person|people|man|woman|actor|model)\b', prompt, re.IGNORECASE):
            characters.append("person")
        return characters

    def _extract_products(self, prompt: str) -> List[str]:
        products = []
        if re.search(r'\b(watch|shoe|phone|laptop|car|product)\b', prompt, re.IGNORECASE):
            products.append("product")
        return products

    def _extract_locations(self, prompt: str) -> List[str]:
        locations = []
        location_patterns = [
            r'\b(?:in|at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b(city|beach|forest|desert|office|store|home|studio|street)\b',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, prompt)
            locations.extend(matches)
        return locations[:5]

    def _extract_audio(self, prompt: str) -> Dict[str, Any]:
        audio = {}
        if "music" in prompt.lower():
            audio["music"] = True
        if "voiceover" in prompt.lower() or "voice over" in prompt.lower():
            audio["voiceover"] = True
        if "sound effect" in prompt.lower() or "sfx" in prompt.lower():
            audio["sfx"] = True
        if "ambient" in prompt.lower() or "ambience" in prompt.lower():
            audio["ambient"] = True
        return audio

    def _extract_cta(self, prompt: str) -> Optional[str]:
        cta_match = re.search(r'\b(buy now|shop now|learn more|sign up|subscribe|download|visit)\b', prompt, re.IGNORECASE)
        if cta_match:
            return cta_match.group(0)
        return None

    def _plan_scenes(self, intent: IntentExtraction, references: List[str]) -> List[ScenePlan]:
        duration = intent.total_duration_seconds
        scenes = []

        if intent.content_type == "commercial" or intent.content_type == "advertisement":
            scenes = self._plan_commercial_scenes(intent, duration)
        elif intent.content_type == "social":
            scenes = self._plan_social_scenes(intent, duration)
        elif intent.content_type == "cinematic":
            scenes = self._plan_cinematic_scenes(intent, duration)
        else:
            scenes = self._plan_default_scenes(intent, duration)

        return scenes

    def _plan_commercial_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        num_scenes = max(2, min(4, duration // 8))

        if num_scenes == 2:
            scenes.append(self._create_scene(0, "Product Introduction", "Show the product clearly", duration * 0.4, intent))
            scenes.append(self._create_scene(1, "Product in Action", "Demonstrate product use", duration * 0.6, intent))
        elif num_scenes == 3:
            scenes.append(self._create_scene(0, "Hook", "Grab attention with product", duration * 0.25, intent))
            scenes.append(self._create_scene(1, "Demonstration", "Show product features", duration * 0.45, intent))
            scenes.append(self._create_scene(2, "CTA", "Call to action with product", duration * 0.3, intent))
        else:
            scenes.append(self._create_scene(0, "Hook", "Grab attention", duration * 0.2, intent))
            scenes.append(self._create_scene(1, "Feature 1", "Show key feature", duration * 0.25, intent))
            scenes.append(self._create_scene(2, "Feature 2", "Show another feature", duration * 0.25, intent))
            scenes.append(self._create_scene(3, "CTA", "Call to action", duration * 0.3, intent))

        return scenes

    def _plan_social_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        scenes.append(self._create_scene(0, "Hook", "Quick attention grabber", duration * 0.3, intent))
        scenes.append(self._create_scene(1, "Content", "Main content", duration * 0.5, intent))
        scenes.append(self._create_scene(2, "CTA", "Call to action", duration * 0.2, intent))
        return scenes

    def _plan_cinematic_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        num_scenes = max(2, min(5, duration // 10))
        scene_duration = duration / num_scenes

        for i in range(num_scenes):
            purpose = f"Scene {i + 1}"
            if i == 0:
                purpose = "Establishing shot"
            elif i == num_scenes - 1:
                purpose = "Conclusion"
            scenes.append(self._create_scene(i, purpose, f"Scene {i + 1} of the story", scene_duration, intent))

        return scenes

    def _plan_default_scenes(self, intent: IntentExtraction, duration: int) -> List[ScenePlan]:
        scenes = []
        scenes.append(self._create_scene(0, "Opening", "Introduction", duration * 0.5, intent))
        scenes.append(self._create_scene(1, "Main", "Main content", duration * 0.5, intent))
        return scenes

    def _create_scene(self, order: int, name: str, purpose: str, duration: float, intent: IntentExtraction) -> ScenePlan:
        num_shots = max(1, min(4, int(duration / 5)))
        shots = self._plan_shots(order, num_shots, duration, intent)

        return ScenePlan(
            id=str(uuid.uuid4()),
            order=order,
            name=name,
            purpose=purpose,
            environment=intent.locations[0] if intent.locations else None,
            duration_seconds=duration,
            shots=shots,
            references=[],
            characters=intent.characters.copy(),
            products=intent.products.copy(),
            locations=intent.locations.copy(),
            continuity=[],
        )

    def _plan_shots(self, scene_id: int, num_shots: int, scene_duration: float, intent: IntentExtraction) -> List[ShotPlan]:
        shots = []
        shot_duration = scene_duration / num_shots

        for i in range(num_shots):
            shot = ShotPlan(
                id=str(uuid.uuid4()),
                scene_id=str(scene_id),
                order=i,
                description=f"Shot {i + 1}",
                subject=intent.subject,
                action=None,
                environment=intent.locations[0] if intent.locations else None,
                camera=CameraRequirement(),
                lighting=None,
                composition=None,
                style=intent.style,
                motion=None,
                duration_seconds=shot_duration,
                references=[],
                characters=intent.characters.copy(),
                products=intent.products.copy(),
                locations=intent.locations.copy(),
                audio=[],
                continuity=[],
                generation=None,
                status="planned",
            )
            shots.append(shot)

        return shots

    def _extract_asset_requirements(self, intent: IntentExtraction, scenes: List[ScenePlan], references: List[str]) -> List[AssetRequirement]:
        requirements = []

        if intent.characters:
            requirements.append(AssetRequirement(
                id=str(uuid.uuid4()),
                type="character",
                role="character",
                description="Character reference for consistency",
                required=len(intent.characters) > 0,
            ))

        if intent.products:
            requirements.append(AssetRequirement(
                id=str(uuid.uuid4()),
                type="product",
                role="product",
                description="Product reference for consistency",
                required=len(intent.products) > 0,
            ))

        if intent.locations:
            requirements.append(AssetRequirement(
                id=str(uuid.uuid4()),
                type="location",
                role="location",
                description="Location reference for consistency",
                required=len(intent.locations) > 0,
            ))

        return requirements

    def _extract_continuity_requirements(self, scenes: List[ScenePlan]) -> List[ContinuityRequirement]:
        requirements = []

        for scene in scenes:
            if scene.characters:
                requirements.append(ContinuityRequirement(
                    id=str(uuid.uuid4()),
                    type="character",
                    description=f"Maintain character consistency in {scene.name}",
                    applies_to=[s.id for s in scene.shots],
                ))
            if scene.products:
                requirements.append(ContinuityRequirement(
                    id=str(uuid.uuid4()),
                    type="product",
                    description=f"Maintain product consistency in {scene.name}",
                    applies_to=[s.id for s in scene.shots],
                ))

        return requirements

    def _extract_audio_requirements(self, intent: IntentExtraction, scenes: List[ScenePlan]) -> List[AudioRequirement]:
        requirements = []
        total_duration = sum(s.duration_seconds for s in scenes)

        if intent.voiceover:
            requirements.append(AudioRequirement(
                id=str(uuid.uuid4()),
                type="voiceover",
                description="Voiceover narration",
                duration_seconds=total_duration,
                parameters={"tone": intent.tone},
            ))

        if intent.music:
            requirements.append(AudioRequirement(
                id=str(uuid.uuid4()),
                type="music",
                description="Background music",
                duration_seconds=total_duration,
                parameters={"style": intent.style or "cinematic"},
            ))

        return requirements

    def _extract_export_requirements(self, intent: IntentExtraction) -> ExportRequirement:
        fps = 24
        if intent.platform in ["tiktok", "instagram"]:
            fps = 30
        elif intent.platform == "youtube":
            fps = 60

        return ExportRequirement(
            id=str(uuid.uuid4()),
            aspect_ratio=intent.aspect_ratio,
            resolution=intent.resolution,
            fps=fps,
            format="mp4",
            platform=intent.platform,
            duration_seconds=float(intent.total_duration_seconds),
        )

    async def save_plan(self, plan: DirectorPlan) -> DirectorPlan:
        async with async_session_maker() as session:
            db_plan = DirectorPlanModel(
                id=plan.id,
                project_id=plan.project_id,
                prompt=plan.intent.objective,
                intent=plan.intent.model_dump(),
                scenes=[s.model_dump() for s in plan.scenes],
                asset_requirements=[a.model_dump() for a in plan.asset_requirements],
                audio_requirements=[a.model_dump() for a in plan.audio_requirements],
                export_requirements=plan.export_requirements.model_dump(),
                status=plan.status,
                preferences={},
            )
            session.add(db_plan)
            await session.commit()
            await session.refresh(db_plan)
            return plan

    async def get_plan(self, plan_id: str) -> Optional[DirectorPlan]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
            )
            db_plan = result.scalar_one_or_none()
            if not db_plan:
                return None
            return self._model_to_plan(db_plan)

    async def list_plans(self, project_id: str) -> List[DirectorPlan]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DirectorPlanModel)
                .where(DirectorPlanModel.project_id == project_id)
                .order_by(DirectorPlanModel.created_at.desc())
            )
            plans = result.scalars().all()
            return [self._model_to_plan(p) for p in plans]

    async def update_plan_status(self, plan_id: str, status: str) -> Optional[DirectorPlan]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
            )
            db_plan = result.scalar_one_or_none()
            if not db_plan:
                return None
            db_plan.status = status
            await session.commit()
            await session.refresh(db_plan)
            return self._model_to_plan(db_plan)

    def _model_to_plan(self, db_plan: DirectorPlanModel) -> DirectorPlan:
        intent = IntentExtraction(**db_plan.intent)
        scenes = [ScenePlan(**s) for s in db_plan.scenes]
        asset_requirements = [AssetRequirement(**a) for a in db_plan.asset_requirements]
        audio_requirements = [AudioRequirement(**a) for a in db_plan.audio_requirements]
        export_requirements = ExportRequirement(**db_plan.export_requirements)
        continuity_requirements = []

        return DirectorPlan(
            id=db_plan.id,
            project_id=db_plan.project_id,
            intent=intent,
            scenes=scenes,
            asset_requirements=asset_requirements,
            continuity_requirements=continuity_requirements,
            audio_requirements=audio_requirements,
            export_requirements=export_requirements,
            status=db_plan.status,
            created_at=db_plan.created_at,
            updated_at=db_plan.updated_at,
        )


from sqlalchemy import select

director_service = DirectorService()
