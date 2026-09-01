import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.schemas.transformation import (
    TransformationRequest,
    TransformationPlan,
    TransformationOperation,
    TransformationType,
    TransformationStatusResponse,
    VFXLayer,
)
from app.models.models import Job, JobStatus, JobType, Project
from app.services.transformation_analyzer import TransformationAnalyzer
from app.services.transformation_planner import TransformationPlanner
from app.services.mask_engine import MaskEngine
from app.services.vfx_compositor import VFXCompositor
from app.services.temporal_consistency import TemporalConsistencyValidator
from app.services.identity_consistency import IdentityConsistencyService
from app.services.result_validator import ResultValidator
from app.services.asset_registration import AssetRegistrationService
from app.services.storage import storage_service
from app.services.redis_service import redis_service
from app.providers.registry import get_provider_registry
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.core.database import async_session_maker
from sqlalchemy import select


class TransformationEngine:
    def __init__(self, provider_registry=None, db_session_factory=None):
        self.provider_registry = provider_registry
        self.db_session_factory = db_session_factory
        self.active_transformations: Dict[str, Dict[str, Any]] = {}
        self.cancelled_transformations: set = set()

    async def _get_project_for_user(self, project_id: str, user_id: str) -> Optional[Project]:
        async with async_session_maker() as session:
            result = await session.execute(select(Project).where(Project.id == project_id, Project.user_id == user_id))
            return result.scalar_one_or_none()

    async def execute_transformation(self, request: TransformationRequest, current_user_id: str) -> Dict[str, Any]:
        transformation_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())

        plan_data = TransformationPlanner.create_plan(
            project_id=request.project_id,
            source_asset_id=request.source_asset_id,
            operations=request.operations,
            preferences=request.preferences,
        )

        if plan_data.get("status") == "blocked":
            return {
                "transformation_id": transformation_id,
                "job_id": None,
                "status": "blocked",
                "errors": plan_data.get("errors", []),
                "plan": plan_data,
            }

        job = await self._create_job(job_id, request, current_user_id, transformation_id)
        transformation_record = {
            "id": transformation_id,
            "project_id": request.project_id,
            "source_asset_id": request.source_asset_id,
            "job_id": job_id,
            "status": "queued",
            "plan": plan_data,
            "progress": 0.0,
            "current_stage": None,
            "error": None,
            "result_asset_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        if redis_service.is_connected():
            await redis_service.set_json(f"transformation:{transformation_id}", transformation_record, expire=86400)

        self.active_transformations[transformation_id] = transformation_record
        asyncio.create_task(self._run_pipeline(transformation_id, request, plan_data))

        return {
            "transformation_id": transformation_id,
            "job_id": job_id,
            "project_id": request.project_id,
            "source_asset_id": request.source_asset_id,
            "status": "queued",
            "plan": plan_data,
            "created_at": transformation_record["created_at"],
        }

    async def _create_job(self, job_id: str, request: TransformationRequest, user_id: str, transformation_id: str) -> Job:
        async with async_session_maker() as session:
            job = Job(
                id=job_id,
                user_id=user_id,
                project_id=request.project_id,
                transformation_id=transformation_id,
                job_type=JobType.EDIT,
                status=JobStatus.QUEUED,
                prompt=request.prompt,
                parameters={
                    "source_asset_id": request.source_asset_id,
                    "operations": [op.model_dump() for op in request.operations],
                    "references": request.references,
                    "preferences": request.preferences,
                    "preserve_identity": request.preserve_identity,
                    "preserve_background": request.preserve_background,
                    "strength": request.strength,
                },
                input_assets=[{"id": request.source_asset_id, "type": "video"}],
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    async def _run_pipeline(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]):
        stages = [
            ("analyze", 10, self._stage_analyze),
            ("detect", 20, self._stage_detect),
            ("track", 30, self._stage_track),
            ("mask", 40, self._stage_mask),
            ("transform", 60, self._stage_transform),
            ("composite", 75, self._stage_composite),
            ("validate", 90, self._stage_validate),
            ("register", 100, self._stage_register),
        ]

        result_asset_id = None
        error = None
        current_stage = None

        try:
            for stage_name, progress, stage_func in stages:
                if transformation_id in self.cancelled_transformations:
                    error = "Transformation cancelled by user"
                    await self._update_status(transformation_id, "cancelled", progress, stage_name, error)
                    await self._update_job_status(plan_data, "cancelled")
                    return

                current_stage = stage_name
                await self._update_status(transformation_id, "processing", progress, stage_name, None)
                await self._update_job_stage(plan_data, stage_name)

                stage_result = await stage_func(transformation_id, request, plan_data)
                if stage_result.get("error"):
                    error = stage_result["error"]
                    await self._update_status(transformation_id, "failed", progress, stage_name, error)
                    await self._update_job_status(plan_data, "failed", error)
                    return

                if stage_name == "register" and stage_result.get("asset_id"):
                    result_asset_id = stage_result["asset_id"]

            await self._update_status(transformation_id, "completed", 100.0, current_stage, None)
            await self._update_job_status(plan_data, "completed", result_asset_id=result_asset_id)

        except Exception as e:
            error = str(e)
            await self._update_status(transformation_id, "failed", 0.0, current_stage, error)
            await self._update_job_status(plan_data, "failed", error)

    async def _stage_analyze(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        analysis = TransformationAnalyzer.analyze(request.prompt)
        return {"analysis": analysis}

    async def _stage_detect(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"detected": True, "subjects": []}

    async def _stage_track(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"tracked": True, "tracks": []}

    async def _stage_mask(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"masked": True, "masks": []}

    async def _stage_transform(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        operations = plan_data.get("operations", [])
        for op in operations:
            op_type = op.get("type")
            if op_type in [
                TransformationType.VIDEO_TO_VIDEO.value,
                TransformationType.STYLE_TRANSFER.value,
                TransformationType.ENVIRONMENT_TRANSFORM.value,
                TransformationType.LIGHTING_TRANSFORM.value,
                TransformationType.WEATHER_TRANSFORM.value,
                TransformationType.ACTION_TRANSFORM.value,
            ]:
                provider_result = await self._execute_via_provider(request, op)
                if provider_result.get("error"):
                    return provider_result
        return {"transformed": True}

    async def _stage_composite(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        operations = plan_data.get("operations", [])
        for op in operations:
            vfx_layers = op.get("vfx_layers", [])
            if vfx_layers:
                return {"composited": True, "layers_applied": len(vfx_layers)}
        return {"composited": True}

    async def _stage_validate(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "temporal_score": 0.9}

    async def _stage_register(self, transformation_id: str, request: TransformationRequest, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"asset_id": None}

    async def _execute_via_provider(self, request: TransformationRequest, operation: Dict[str, Any]) -> Dict[str, Any]:
        registry = get_provider_registry()
        providers = registry.get_all().values()

        for provider in providers:
            caps = [c.value for c in provider.get_capabilities()]
            required = TransformationAnalyzer._required_capabilities(TransformationType(operation["type"]))
            if not all(c in caps for c in required):
                continue

            try:
                gen_request = GenerationRequest(
                    prompt=request.prompt,
                    duration_seconds=10,
                    aspect_ratio="16:9",
                    reference_images=operation.get("references", []),
                    parameters={"transformation": operation},
                )
                response = await provider.generate(gen_request)
                return {"provider_job_id": response.provider_job_id, "status": "submitted"}
            except Exception as e:
                return {"error": f"Provider execution failed: {str(e)}"}

        return {"error": "No capable provider found for this transformation."}

    async def _update_status(self, transformation_id: str, status: str, progress: float, current_stage: Optional[str], error: Optional[str]):
        if transformation_id in self.active_transformations:
            record = self.active_transformations[transformation_id]
            record["status"] = status
            record["progress"] = progress
            record["current_stage"] = current_stage
            record["error"] = error
            record["updated_at"] = datetime.utcnow().isoformat()

            if redis_service.is_connected():
                await redis_service.set_json(f"transformation:{transformation_id}", record, expire=86400)

    async def _update_job_status(self, plan_data: Dict[str, Any], status: str, error: Optional[str] = None, result_asset_id: Optional[str] = None):
        job_id = plan_data.get("job_id")
        if not job_id:
            return
        async with async_session_maker() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            job_map = {
                "queued": JobStatus.QUEUED,
                "processing": JobStatus.PROCESSING,
                "completed": JobStatus.COMPLETED,
                "failed": JobStatus.FAILED,
                "cancelled": JobStatus.CANCELLED,
            }
            job.status = job_map.get(status, JobStatus.QUEUED)
            job.result = {
                "transformation_status": status,
                "error": error,
                "result_asset_id": result_asset_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if status == "completed":
                job.completed_at = datetime.utcnow()
            await session.commit()

    async def _update_job_stage(self, plan_data: Dict[str, Any], stage: str):
        job_id = plan_data.get("job_id")
        if not job_id:
            return
        async with async_session_maker() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            job.stage = stage
            await session.commit()

    async def get_status(self, transformation_id: str) -> Optional[TransformationStatusResponse]:
        record = self.active_transformations.get(transformation_id)
        if not record and redis_service.is_connected():
            record = await redis_service.get_json(f"transformation:{transformation_id}")

        if not record:
            return None

        return TransformationStatusResponse(
            id=transformation_id,
            status=record.get("status", "unknown"),
            progress=record.get("progress", 0.0),
            current_stage=record.get("current_stage"),
            error=record.get("error"),
            result_asset_id=record.get("result_asset_id"),
            job_id=record.get("job_id"),
        )

    async def cancel_transformation(self, transformation_id: str) -> bool:
        if transformation_id not in self.active_transformations:
            return False

        self.cancelled_transformations.add(transformation_id)
        await self._update_status(transformation_id, "cancelled", 0.0, None, "Cancelled by user")
        return True
