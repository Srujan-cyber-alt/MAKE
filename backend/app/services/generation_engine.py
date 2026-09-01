import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Job, JobStatus, DirectorPlan as DirectorPlanModel
from app.schemas.director import DirectorPlan, ScenePlan, ShotPlan, GenerationRequirement
from app.services.model_router import ModelRouter, ModelSelection
from app.services.prompt_compiler import PromptCompiler
from app.services.generation_planner import GenerationPlanner
from app.services.result_validator import ResultValidator, ValidationResult
from app.services.asset_registration import asset_registration_service
from app.services.provider_health import provider_health_service
from app.services.orchestrator import JobOrchestrator
from app.services.storage import storage_service
from app.providers.base import ProviderRegistry, GenerationRequest as ProviderGenerationRequest
from app.core.database import async_session_maker


class GenerationEngine:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        orchestrator: JobOrchestrator,
        storage_service_instance=None,
    ):
        self.provider_registry = provider_registry
        self.orchestrator = orchestrator
        self.storage = storage_service_instance or storage_service
        self.model_router = ModelRouter(provider_registry)
        self.prompt_compiler = PromptCompiler()
        self.generation_planner = GenerationPlanner()
        self.result_validator = ResultValidator()

    async def execute_shot(
        self,
        plan: DirectorPlan,
        scene: ScenePlan,
        shot: ShotPlan,
        user_id: str,
        preferences: Dict[str, Any] = None,
        idempotency_key: str = None,
    ) -> Optional[Job]:
        preferences = preferences or {}

        if not shot.generation or not shot.generation.method:
            return None

        model_selection = await self.model_router.route(shot.generation, shot, preferences)
        provider = self.provider_registry.get(model_selection.provider_id)
        if not provider:
            raise ValueError(f"Provider {model_selection.provider_id} not found")

        compiled_prompt = self.prompt_compiler.compile(shot, plan)
        negative_prompt = self.prompt_compiler.extract_negative_prompt(shot, plan)

        job = Job(
            user_id=user_id,
            project_id=plan.project_id,
            job_type=shot.generation.method.upper().replace("_", "_"),
            provider=model_selection.provider_id,
            model=model_selection.model_id,
            prompt=compiled_prompt,
            negative_prompt=negative_prompt,
            parameters={
                "duration_seconds": shot.duration_seconds,
                "aspect_ratio": plan.aspect_ratio,
                "width": self._parse_width(plan.resolution),
                "height": self._parse_height(plan.resolution),
                "fps": 24,
                "seed": None,
                "guidance_scale": 7.5,
                "reference_images": [{"url": r, "type": "reference"} for r in (shot.references or [])],
                "plan_id": plan.id,
                "scene_id": scene.id,
                "shot_id": shot.id,
                "model_selection": {
                    "score": model_selection.score,
                    "reasons": model_selection.reasons,
                    "estimated_cost": model_selection.estimated_cost,
                    "fallback_models": model_selection.fallback_models,
                },
            },
            input_assets=[],
            status=JobStatus.QUEUED,
        )

        async with async_session_maker() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)

        return job

    async def execute_plan(
        self,
        plan: DirectorPlan,
        user_id: str,
        shot_ids: List[str] = None,
        scene_ids: List[str] = None,
        preferences: Dict[str, Any] = None,
    ) -> List[Job]:
        jobs = []
        for scene in plan.scenes:
            if scene_ids and scene.id not in scene_ids:
                continue
            for shot in scene.shots:
                if shot_ids and shot.id not in shot_ids:
                    continue
                job = await self.execute_shot(plan, scene, shot, user_id, preferences)
                if job:
                    jobs.append(job)
        return jobs

    async def get_generation_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            provider = self.provider_registry.get(job.provider) if job.provider else None
            provider_status = None
            if provider and job.result and job.result.get("provider_job_id"):
                try:
                    provider_status = await provider.check_status(job.result["provider_job_id"])
                except Exception:
                    pass

            return {
                "job_id": job.id,
                "status": job.status.value if job.status else None,
                "provider_status": provider_status.status if provider_status else None,
                "provider": job.provider,
                "model": job.model,
                "prompt": job.prompt,
                "result": job.result,
                "error": job.error,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }

    async def cancel_generation(self, job_id: str) -> bool:
        return await self.orchestrator.cancel_job(job_id)

    def _parse_width(self, resolution: str) -> Optional[int]:
        if not resolution:
            return None
        if "x" in resolution.lower():
            try:
                return int(resolution.lower().split("x")[0])
            except (ValueError, IndexError):
                pass
        return {"1080p": 1920, "720p": 1280, "4k": 3840}.get(resolution)

    def _parse_height(self, resolution: str) -> Optional[int]:
        if not resolution:
            return None
        if "x" in resolution.lower():
            try:
                return int(resolution.lower().split("x")[1])
            except (ValueError, IndexError):
                pass
        return {"1080p": 1080, "720p": 720, "4k": 2160}.get(resolution)


generation_engine = GenerationEngine(
    provider_registry=None,
    orchestrator=None,
)
