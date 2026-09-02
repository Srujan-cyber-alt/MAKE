from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, User
from app.services.studio_orchestrator import StudioOrchestrator, CreationMode
from app.services.capability_registry import CapabilityRegistry
from app.services.real_time_progress import RealTimeProgress
import uuid

router = APIRouter()


@router.get("/projects/{project_id}")
async def get_studio_project(project_id: str, current_user: User = Depends(get_current_user)):
    return {
        "project_id": project_id,
        "user_id": current_user.id,
        "modes": [
            {"id": CreationMode.CREATE, "label": "Create", "icon": "Sparkles"},
            {"id": CreationMode.EDIT, "label": "Edit", "icon": "Scissors"},
            {"id": CreationMode.TRANSFORM, "label": "Transform", "icon": "RefreshCw"},
            {"id": CreationMode.ANIMATE, "label": "Animate", "icon": "PlayCircle"},
            {"id": CreationMode.EXTEND, "label": "Extend", "icon": "PlusCircle"},
            {"id": CreationMode.REMIX, "label": "Remix", "icon": "Copy"},
            {"id": CreationMode.AUTO, "label": "Auto", "icon": "Wand2"},
        ],
    }


@router.post("/projects/{project_id}/command")
async def execute_studio_command(
    project_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    command = request.get("command", "")
    mode = request.get("mode", CreationMode.AUTO)
    context = request.get("context", {})

    if not command.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Command is required")

    result = await StudioOrchestrator.route_command(
        command=command,
        project_id=project_id,
        user_id=current_user.id,
        mode=mode,
        context=context,
    )
    return result


@router.get("/projects/{project_id}/capabilities")
async def get_studio_capabilities(project_id: str, current_user: User = Depends(get_current_user)):
    capabilities = await CapabilityRegistry.get_all_capabilities()
    return capabilities


@router.get("/projects/{project_id}/progress/{job_id}")
async def get_studio_progress(project_id: str, job_id: str, current_user: User = Depends(get_current_user)):
    progress = await RealTimeProgress.get_progress(job_id)
    return progress


@router.get("/projects/{project_id}/assets")
async def get_studio_assets(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.models import Asset

    result = await db.execute(
        select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    return [
        {
            "id": asset.id,
            "filename": asset.filename,
            "asset_type": asset.asset_type.value if asset.asset_type else None,
            "status": asset.status.value if asset.status else None,
            "duration_seconds": asset.duration_seconds,
            "width": asset.width,
            "height": asset.height,
            "fps": asset.fps,
            "storage_url": asset.storage_url,
            "thumbnail_path": asset.thumbnail_path,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }
        for asset in assets
    ]


@router.get("/projects/{project_id}/versions")
async def get_studio_versions(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.models import ProjectVersion

    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.project_id == project_id).order_by(ProjectVersion.created_at.desc())
    )
    versions = result.scalars().all()
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "name": v.name,
            "description": v.description,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.post("/projects/{project_id}/versions")
async def create_studio_version(project_id: str, request: Dict[str, Any], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.models import ProjectVersion

    version = ProjectVersion(
        project_id=project_id,
        version_number=request.get("version_number") or 1,
        name=request.get("name", f"Version {uuid.uuid4().hex[:6]}"),
        description=request.get("description", ""),
        snapshot=request.get("snapshot", {}),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return {
        "id": version.id,
        "version_number": version.version_number,
        "name": version.name,
        "description": version.description,
    }


@router.post("/projects/{project_id}/export")
async def create_studio_export(project_id: str, request: Dict[str, Any], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.export_engine import ExportEngine
    from app.services.storage import storage_service

    result = await ExportEngine.export_project(
        project_id=project_id,
        user_id=current_user.id,
        export_format=request.get("format", "mp4"),
        resolution=request.get("resolution", "1920x1080"),
        fps=request.get("fps", 30),
        platform=request.get("platform"),
        include_captions=request.get("include_captions", False),
    )
    return result


@router.post("/projects/{project_id}/undo")
async def studio_undo(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.timeline_service import TimelineService
    from app.core.database import async_session_maker
    from sqlalchemy import select
    from app.models.models import Timeline

    async with async_session_maker() as session:
        result = await session.execute(select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc()))
        timeline = result.scalar_one_or_none()
        if not timeline:
            return {"status": "no_timeline"}
        timeline_data = {
            "timeline_id": timeline.id,
            "project_id": timeline.project_id,
            "name": timeline.name,
            "duration_seconds": timeline.duration_seconds,
            "fps": timeline.fps,
            "resolution": timeline.resolution,
            "tracks": timeline.tracks or {},
            "settings": timeline.settings or {},
            "history": (timeline.settings or {}).get("history", []),
            "history_index": (timeline.settings or {}).get("history_index", -1),
            "clips": (timeline.tracks or {}).get("clips", []),
            "keyframes": (timeline.tracks or {}).get("keyframes", []),
            "transitions": (timeline.tracks or {}).get("transitions", []),
            "audio_tracks": (timeline.tracks or {}).get("audio_tracks", []),
            "caption_tracks": (timeline.tracks or {}).get("caption_tracks", []),
            "vfx_layers": (timeline.tracks or {}).get("vfx_layers", []),
        }
        updated = await TimelineService.undo(timeline_data)
        timeline.tracks = {
            "clips": updated.get("clips", []),
            "keyframes": updated.get("keyframes", []),
            "transitions": updated.get("transitions", []),
            "audio_tracks": updated.get("audio_tracks", []),
            "caption_tracks": updated.get("caption_tracks", []),
            "vfx_layers": updated.get("vfx_layers", []),
        }
        timeline.settings = {
            **(timeline.settings or {}),
            "history": updated.get("history", []),
            "history_index": updated.get("history_index", -1),
        }
        await session.commit()
        return {"status": "undone", "history_index": updated.get("history_index", -1)}


@router.post("/projects/{project_id}/redo")
async def studio_redo(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.timeline_service import TimelineService
    from app.core.database import async_session_maker
    from sqlalchemy import select
    from app.models.models import Timeline

    async with async_session_maker() as session:
        result = await session.execute(select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc()))
        timeline = result.scalar_one_or_none()
        if not timeline:
            return {"status": "no_timeline"}
        timeline_data = {
            "timeline_id": timeline.id,
            "project_id": timeline.project_id,
            "name": timeline.name,
            "duration_seconds": timeline.duration_seconds,
            "fps": timeline.fps,
            "resolution": timeline.resolution,
            "tracks": timeline.tracks or {},
            "settings": timeline.settings or {},
            "history": (timeline.settings or {}).get("history", []),
            "history_index": (timeline.settings or {}).get("history_index", -1),
            "clips": (timeline.tracks or {}).get("clips", []),
            "keyframes": (timeline.tracks or {}).get("keyframes", []),
            "transitions": (timeline.tracks or {}).get("transitions", []),
            "audio_tracks": (timeline.tracks or {}).get("audio_tracks", []),
            "caption_tracks": (timeline.tracks or {}).get("caption_tracks", []),
            "vfx_layers": (timeline.tracks or {}).get("vfx_layers", []),
        }
        updated = await TimelineService.redo(timeline_data)
        timeline.tracks = {
            "clips": updated.get("clips", []),
            "keyframes": updated.get("keyframes", []),
            "transitions": updated.get("transitions", []),
            "audio_tracks": updated.get("audio_tracks", []),
            "caption_tracks": updated.get("caption_tracks", []),
            "vfx_layers": updated.get("vfx_layers", []),
        }
        timeline.settings = {
            **(timeline.settings or {}),
            "history": updated.get("history", []),
            "history_index": updated.get("history_index", -1),
        }
        await session.commit()
        return {"status": "redone", "history_index": updated.get("history_index", -1)}


@router.post("/jobs/{job_id}/variation")
async def create_job_variation(job_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.models import Job

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    creative_plan = {
        "genre": "commercial",
        "tone": "cinematic",
        "title": job.prompt or "Variant",
        "prompt": job.prompt or "",
    }

    from app.services.variant_engine import VariantEngine
    result_data = VariantEngine.generate_variants(creative_plan, num_variants=4)
    return result_data


@router.post("/jobs/{job_id}/repair")
async def repair_job(job_id: str, current_user: User = Depends(get_current_user)):
    from app.services.intelligent_shot_repair import IntelligentShotRepair
    from app.services.quality_control import QualityControl

    repair_engine = IntelligentShotRepair(
        quality_control=QualityControl(),
        generation_engine=__import__("app.services.generation_engine", fromlist=["GenerationEngine"]).GenerationEngine(),
    )

    result = await repair_engine.repair_shot(
        job_id=job_id,
        user_id=current_user.id,
    )
    return result
