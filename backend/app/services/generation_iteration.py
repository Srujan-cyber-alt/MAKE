from typing import Optional, List, Dict, Any
from app.schemas.phase9 import GenerationIteration
from app.core.database import async_session_maker
from app.models.models import ProjectVersion
from sqlalchemy import select
import uuid
import logging

logger = logging.getLogger(__name__)


class GenerationIterationSystem:
    @staticmethod
    async def create_iteration(
        project_id: str,
        prompt: str,
        shot_id: Optional[str] = None,
        parent_iteration_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        references: Optional[List[str]] = None,
        seed: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result_asset_id: Optional[str] = None,
        quality_score: Optional[float] = None,
        changes: Optional[List[str]] = None,
    ) -> GenerationIteration:
        iteration_id = str(uuid.uuid4())
        iteration = GenerationIteration(
            iteration_id=iteration_id,
            project_id=project_id,
            shot_id=shot_id,
            parent_iteration_id=parent_iteration_id,
            prompt=prompt,
            provider=provider,
            model=model,
            references=references or [],
            seed=seed,
            parameters=parameters or {},
            result_asset_id=result_asset_id,
            quality_score=quality_score,
            changes=changes or [],
        )

        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            await redis_service.set_json(f"generation_iteration:{iteration_id}", iteration.model_dump(), ex=86400)

        logger.info(f"Created generation iteration {iteration_id} for project {project_id}")
        return iteration

    @staticmethod
    async def get_iteration(iteration_id: str) -> Optional[Dict[str, Any]]:
        if redis_service_is_connected():
            from app.services.redis_service import redis_service
            return await redis_service.get_json(f"generation_iteration:{iteration_id}")
        return None

    @staticmethod
    async def list_iterations(project_id: str, shot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not redis_service_is_connected():
            return []
        from app.services.redis_service import redis_service
        keys = await redis_service.keys(f"generation_iteration:*")
        iterations = []
        for key in keys:
            data = await redis_service.get_json(key)
            if data and data.get("project_id") == project_id:
                if shot_id is None or data.get("shot_id") == shot_id:
                    iterations.append(data)
        return sorted(iterations, key=lambda x: x.get("created_at", ""))

    @staticmethod
    async def create_project_version_from_iteration(
        project_id: str,
        iteration_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        iteration_data = await GenerationIterationSystem.get_iteration(iteration_id)
        if not iteration_data:
            return None

        from app.services.versioning import VersionWorkflow
        return await VersionWorkflow.create_version(
            project_id=project_id,
            prompt=iteration_data.get("prompt", ""),
            operations=[{"type": "generation_iteration", "iteration_id": iteration_id}],
            asset_ids=[iteration_data["result_asset_id"]] if iteration_data.get("result_asset_id") else [],
            user_id=user_id,
            parent_version_id=None,
            name=f"Iteration {iteration_id[:8]}",
        )


def redis_service_is_connected():
    try:
        from app.services.redis_service import redis_service
        return redis_service.is_connected()
    except Exception:
        return False
