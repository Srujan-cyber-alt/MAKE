import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

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
)
from app.models.models import Project, DirectorPlan as DirectorPlanModel
from app.services.intent_analyzer import IntentAnalyzer
from app.services.creative_planner import CreativePlanner
from app.services.scene_planner import ScenePlanner
from app.services.shot_planner import ShotPlanner
from app.services.asset_requirement_analyzer import AssetRequirementAnalyzer
from app.services.continuity_planner import ContinuityPlanner
from app.services.generation_requirement_planner import GenerationRequirementPlanner
from app.services.audio_planner import AudioPlanner
from app.services.export_planner import ExportPlanner
from app.core.database import async_session_maker
from sqlalchemy import select


class DirectorService:
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.creative_planner = CreativePlanner()
        self.scene_planner = ScenePlanner()
        self.shot_planner = ShotPlanner()
        self.asset_analyzer = AssetRequirementAnalyzer()
        self.continuity_planner = ContinuityPlanner()
        self.generation_planner = GenerationRequirementPlanner()
        self.audio_planner = AudioPlanner()
        self.export_planner = ExportPlanner()

    async def create_plan(self, request: DirectorRequest, project_id: Optional[str] = None) -> DirectorPlan:
        intent = self.intent_analyzer.analyze(request.prompt, request.reference_asset_ids, request.preferences)
        scenes = self.scene_planner.plan_scenes(intent, request.reference_asset_ids)
        asset_requirements = self.asset_analyzer.analyze(intent, scenes, request.reference_asset_ids)
        continuity_requirements = self.continuity_planner.plan_continuity(scenes)
        generation_requirements = self.generation_planner.plan_generation(scenes, intent)
        audio_requirements = self.audio_planner.plan_audio(intent, scenes)
        export_requirements = self.export_planner.plan_export(intent)
        creative = self.creative_planner.create_concept(intent)

        plan = DirectorPlan(
            id=str(uuid.uuid4()),
            project_id=project_id or "",
            title=creative["title"],
            creative_concept=creative["concept"],
            objective=creative["objective"],
            content_type=intent.content_type,
            audience=intent.audience,
            tone=intent.tone,
            style=intent.style,
            duration=intent.total_duration_seconds,
            aspect_ratio=intent.aspect_ratio,
            resolution=intent.resolution,
            platform=intent.platform,
            scenes=scenes,
            asset_requirements=asset_requirements,
            continuity_requirements=continuity_requirements,
            audio_requirements=audio_requirements,
            export_requirements=export_requirements,
            generation_requirements=generation_requirements,
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return plan

    async def save_plan(self, plan: DirectorPlan) -> DirectorPlan:
        async with async_session_maker() as session:
            db_plan = DirectorPlanModel(
                id=plan.id,
                project_id=plan.project_id,
                title=plan.title,
                prompt=plan.objective,
                creative_concept=plan.creative_concept,
                intent={
                    "objective": plan.objective,
                    "content_type": plan.content_type,
                    "audience": plan.audience,
                    "tone": plan.tone,
                    "style": plan.style,
                    "total_duration_seconds": plan.duration,
                    "aspect_ratio": plan.aspect_ratio,
                    "resolution": plan.resolution,
                    "platform": plan.platform,
                },
                scenes=[self._scene_to_dict(s) for s in plan.scenes],
                asset_requirements=[a.model_dump() for a in plan.asset_requirements],
                continuity_requirements=[c.model_dump() for c in plan.continuity_requirements],
                audio_requirements=[a.model_dump() for a in plan.audio_requirements],
                export_requirements=plan.export_requirements.model_dump(),
                generation_requirements=[g.model_dump() for g in plan.generation_requirements],
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

    async def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Optional[DirectorPlan]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DirectorPlanModel).where(DirectorPlanModel.id == plan_id)
            )
            db_plan = result.scalar_one_or_none()
            if not db_plan:
                return None
            for field, value in updates.items():
                if hasattr(db_plan, field):
                    setattr(db_plan, field, value)
            await session.commit()
            await session.refresh(db_plan)
            return self._model_to_plan(db_plan)

    def _scene_to_dict(self, scene: ScenePlan) -> Dict[str, Any]:
        return {
            "id": scene.id,
            "order": scene.order,
            "title": scene.title,
            "purpose": scene.purpose,
            "description": scene.description,
            "environment": scene.environment,
            "duration_seconds": scene.duration_seconds,
            "shots": [shot.model_dump() for shot in scene.shots],
            "references": scene.references,
            "characters": scene.characters,
            "products": scene.products,
            "locations": scene.locations,
            "continuity": scene.continuity,
        }

    def _model_to_plan(self, db_plan: DirectorPlanModel) -> DirectorPlan:
        intent = IntentExtraction(
            objective=db_plan.prompt,
            content_type=db_plan.intent.get("content_type", "cinematic"),
            audience=db_plan.intent.get("audience"),
            tone=db_plan.intent.get("tone", "professional"),
            style=db_plan.intent.get("style"),
            total_duration_seconds=db_plan.intent.get("total_duration_seconds", 30),
            aspect_ratio=db_plan.intent.get("aspect_ratio", "16:9"),
            resolution=db_plan.intent.get("resolution", "1080p"),
            platform=db_plan.intent.get("platform"),
            references=db_plan.intent.get("references", []),
            characters=db_plan.intent.get("characters", []),
            products=db_plan.intent.get("products", []),
            locations=db_plan.intent.get("locations", []),
            audio=db_plan.intent.get("audio", {}),
            voiceover=db_plan.intent.get("voiceover", False),
            music=db_plan.intent.get("music", False),
            captions=db_plan.intent.get("captions", False),
            cta=db_plan.intent.get("cta"),
        )

        scenes = []
        for scene_dict in db_plan.scenes:
            shots = [ShotPlan(**shot) for shot in scene_dict.get("shots", [])]
            scenes.append(ScenePlan(
                id=scene_dict["id"],
                order=scene_dict["order"],
                title=scene_dict["title"],
                purpose=scene_dict["purpose"],
                description=scene_dict.get("description", scene_dict["purpose"]),
                environment=scene_dict.get("environment"),
                duration_seconds=scene_dict["duration_seconds"],
                shots=shots,
                references=scene_dict.get("references", []),
                characters=scene_dict.get("characters", []),
                products=scene_dict.get("products", []),
                locations=scene_dict.get("locations", []),
                continuity=scene_dict.get("continuity", []),
            ))

        asset_requirements = [AssetRequirement(**a) for a in db_plan.asset_requirements]
        continuity_requirements = [ContinuityRequirement(**c) for c in db_plan.continuity_requirements]
        audio_requirements = [AudioRequirement(**a) for a in db_plan.audio_requirements]
        export_requirements = ExportRequirement(**db_plan.export_requirements)
        generation_requirements = [GenerationRequirement(**g) for g in db_plan.generation_requirements]

        return DirectorPlan(
            id=db_plan.id,
            project_id=db_plan.project_id,
            title=db_plan.title,
            creative_concept=db_plan.creative_concept,
            objective=intent.objective,
            content_type=intent.content_type,
            audience=intent.audience,
            tone=intent.tone,
            style=intent.style,
            duration=intent.total_duration_seconds,
            aspect_ratio=intent.aspect_ratio,
            resolution=intent.resolution,
            platform=intent.platform,
            scenes=scenes,
            asset_requirements=asset_requirements,
            continuity_requirements=continuity_requirements,
            audio_requirements=audio_requirements,
            export_requirements=export_requirements,
            generation_requirements=generation_requirements,
            status=db_plan.status,
            created_at=db_plan.created_at,
            updated_at=db_plan.updated_at,
        )


director_service = DirectorService()
