import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.phase7 import VersionSnapshot, PromptIterationHistory
from app.core.database import async_session_maker
from app.models.models import Project, ProjectVersion, Job
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class VersionWorkflow:
    @staticmethod
    async def create_version(
        project_id: str,
        prompt: str,
        operations: List[Dict[str, Any]],
        asset_ids: List[str],
        user_id: str,
        parent_version_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> VersionSnapshot:
        async with async_session_maker() as session:
            result = await session.execute(
                select(ProjectVersion).where(ProjectVersion.project_id == project_id).order_by(ProjectVersion.version_number.desc())
            )
            last = result.scalar_one_or_none()
            version_number = (last.version_number + 1) if last else 1

            snapshot = VersionSnapshot(
                version_id=str(uuid.uuid4()),
                project_id=project_id,
                parent_version_id=parent_version_id,
                version_number=version_number,
                name=name or f"Version {version_number}",
                description=description,
                prompt=prompt,
                operations=operations,
                asset_ids=asset_ids,
            )

            db_version = ProjectVersion(
                id=snapshot.version_id,
                project_id=project_id,
                version_number=version_number,
                name=snapshot.name,
                description=snapshot.description,
                snapshot=snapshot.model_dump(),
            )
            session.add(db_version)
            await session.commit()
            await session.refresh(db_version)

            iteration = PromptIterationHistory(
                iteration_id=str(uuid.uuid4()),
                project_id=project_id,
                base_version_id=parent_version_id,
                prompt=prompt,
                operations=operations,
                result_asset_id=asset_ids[0] if asset_ids else None,
            )
            logger.info(f"Created version {version_number} for project {project_id}")
            return snapshot

    @staticmethod
    async def get_version_history(project_id: str) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(ProjectVersion).where(ProjectVersion.project_id == project_id).order_by(ProjectVersion.version_number.asc())
            )
            versions = result.scalars().all()
            return [
                {
                    "version_id": v.id,
                    "version_number": v.version_number,
                    "name": v.name,
                    "description": v.description,
                    "created_at": v.created_at.isoformat(),
                    "snapshot": v.snapshot,
                }
                for v in versions
            ]

    @staticmethod
    async def get_version(version_id: str) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            version = await session.get(ProjectVersion, version_id)
            if not version:
                return None
            return {
                "version_id": version.id,
                "project_id": version.project_id,
                "version_number": version.version_number,
                "name": version.name,
                "description": version.description,
                "snapshot": version.snapshot,
                "created_at": version.created_at.isoformat(),
            }

    @staticmethod
    async def restore_version(version_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        version = await VersionWorkflow.get_version(version_id)
        if not version:
            return None
        snapshot = version.get("snapshot", {})
        new_snapshot = await VersionWorkflow.create_version(
            project_id=version["project_id"],
            prompt=snapshot.get("prompt", ""),
            operations=snapshot.get("operations", []),
            asset_ids=snapshot.get("asset_ids", []),
            user_id=user_id,
            parent_version_id=version_id,
            name=f"Restored from v{version['version_number']}",
            description=f"Restored from version {version['version_number']}",
        )
        return {
            "version_id": new_snapshot.version_id,
            "version_number": new_snapshot.version_number,
            "restored_from": version_id,
        }
