from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, Timeline
from app.schemas.schemas import TimelineCreate, TimelineResponse
from app.services.timeline_service import TimelineService

router = APIRouter()


@router.post("/{project_id}", response_model=TimelineResponse, status_code=status.HTTP_201_CREATED)
async def create_timeline(
    project_id: str,
    timeline_data: TimelineCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    timeline = Timeline(
        project_id=project_id,
        name=timeline_data.name,
        duration_seconds=timeline_data.duration_seconds,
        fps=timeline_data.fps,
        resolution=timeline_data.resolution,
        tracks=timeline_data.tracks,
        settings=timeline_data.settings,
    )
    db.add(timeline)
    await db.commit()
    await db.refresh(timeline)
    return timeline


@router.get("/{project_id}", response_model=list[TimelineResponse])
async def list_timelines(
    project_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    result = await db.execute(
        select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc())
    )
    return result.scalars().all()


@router.get("/detail/{timeline_id}", response_model=Dict[str, Any])
async def get_timeline(
    timeline_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {
        "timeline_id": timeline.id,
        "project_id": timeline.project_id,
        "name": timeline.name,
        "duration_seconds": timeline.duration_seconds,
        "fps": timeline.fps,
        "resolution": timeline.resolution,
        "tracks": timeline.tracks,
        "settings": timeline.settings,
        "created_at": timeline.created_at.isoformat() if timeline.created_at else None,
        "updated_at": timeline.updated_at.isoformat() if timeline.updated_at else None,
    }


@router.post("/{timeline_id}/clips")
async def add_clip(
    timeline_id: str,
    clip: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    clips = tracks.get("clips", [])
    clip["clip_id"] = str(uuid.uuid4())
    clip["created_at"] = datetime.utcnow().isoformat()
    clips.append(clip)
    tracks["clips"] = clips
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"clip_id": clip["clip_id"], "status": "added"}


@router.post("/{timeline_id}/tracks")
async def add_track(
    timeline_id: str,
    track: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    track_list = tracks.get("tracks", [])
    track["track_id"] = str(uuid.uuid4())
    track["created_at"] = datetime.utcnow().isoformat()
    track_list.append(track)
    tracks["tracks"] = track_list
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"track_id": track["track_id"], "status": "added"}


@router.post("/{timeline_id}/keyframes")
async def add_keyframe(
    timeline_id: str,
    keyframe: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    keyframes = tracks.get("keyframes", [])
    keyframe["keyframe_id"] = str(uuid.uuid4())
    keyframe["created_at"] = datetime.utcnow().isoformat()
    keyframes.append(keyframe)
    tracks["keyframes"] = keyframes
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"keyframe_id": keyframe["keyframe_id"], "status": "added"}


@router.post("/{timeline_id}/transitions")
async def add_transition(
    timeline_id: str,
    transition: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    transitions = tracks.get("transitions", [])
    transition["transition_id"] = str(uuid.uuid4())
    transition["created_at"] = datetime.utcnow().isoformat()
    transitions.append(transition)
    tracks["transitions"] = transitions
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"transition_id": transition["transition_id"], "status": "added"}


@router.post("/{timeline_id}/audio")
async def add_audio_track(
    timeline_id: str,
    audio_track: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    audio_tracks = tracks.get("audio_tracks", [])
    audio_track["track_id"] = str(uuid.uuid4())
    audio_track["created_at"] = datetime.utcnow().isoformat()
    audio_tracks.append(audio_track)
    tracks["audio_tracks"] = audio_tracks
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"track_id": audio_track["track_id"], "status": "added"}


@router.post("/{timeline_id}/captions")
async def add_caption_track(
    timeline_id: str,
    caption_track: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    caption_tracks = tracks.get("caption_tracks", [])
    caption_track["track_id"] = str(uuid.uuid4())
    caption_track["created_at"] = datetime.utcnow().isoformat()
    caption_tracks.append(caption_track)
    tracks["caption_tracks"] = caption_tracks
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"track_id": caption_track["track_id"], "status": "added"}


@router.post("/{timeline_id}/vfx")
async def add_vfx_layer(
    timeline_id: str,
    vfx_layer: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    vfx_layers = tracks.get("vfx_layers", [])
    vfx_layer["layer_id"] = str(uuid.uuid4())
    vfx_layer["created_at"] = datetime.utcnow().isoformat()
    vfx_layers.append(vfx_layer)
    tracks["vfx_layers"] = vfx_layers
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"layer_id": vfx_layer["layer_id"], "status": "added"}


@router.post("/{timeline_id}/trim")
async def trim_clip(
    timeline_id: str,
    clip_id: str,
    start: float,
    end: float,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    clips = tracks.get("clips", [])
    for clip in clips:
        if clip.get("clip_id") == clip_id:
            clip["trim_start"] = start
            clip["trim_end"] = end
            break
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"clip_id": clip_id, "status": "trimmed"}


@router.post("/{timeline_id}/split")
async def split_clip(
    timeline_id: str,
    clip_id: str,
    split_time: float,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    tracks = timeline.tracks or {}
    clips = tracks.get("clips", [])
    for i, clip in enumerate(clips):
        if clip.get("clip_id") == clip_id:
            clip_start = clip.get("start_time", 0)
            if split_time <= clip_start:
                continue
            new_clip = clip.copy()
            new_clip["clip_id"] = str(uuid.uuid4())
            new_clip["start_time"] = split_time
            new_clip["created_at"] = datetime.utcnow().isoformat()
            clip["end_time"] = split_time
            clips.insert(i + 1, new_clip)
            break
    tracks["clips"] = clips
    timeline.tracks = tracks
    timeline.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(timeline)
    return {"clip_id": clip_id, "status": "split"}


@router.post("/{timeline_id}/undo")
async def undo_timeline(
    timeline_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    settings = timeline.settings or {}
    history = settings.get("history", [])
    history_index = settings.get("history_index", -1)
    if history_index > 0:
        history_index -= 1
        state = history[history_index]["state"]
        timeline.tracks = state.get("tracks", timeline.tracks)
        settings["history_index"] = history_index
        timeline.settings = settings
        timeline.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(timeline)
    return {"status": "undone", "history_index": history_index}


@router.post("/{timeline_id}/redo")
async def redo_timeline(
    timeline_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timeline = await db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    project = await db.get(Project, timeline.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    settings = timeline.settings or {}
    history = settings.get("history", [])
    history_index = settings.get("history_index", -1)
    if history_index < len(history) - 1:
        history_index += 1
        state = history[history_index]["state"]
        timeline.tracks = state.get("tracks", timeline.tracks)
        settings["history_index"] = history_index
        timeline.settings = settings
        timeline.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(timeline)
    return {"status": "redone", "history_index": history_index}
