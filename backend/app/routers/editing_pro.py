"""
Phase 17 Editing API Router.
"""

from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.professional_timeline_engine import professional_timeline_engine, Track, TrackType, Clip
from app.services.non_destructive_editing_engine import non_destructive_editing_engine, EditOperationType
from app.services.transitions_engine import transitions_engine, TransitionType
from app.services.advanced_keyframe_engine import advanced_keyframe_engine, InterpolationType
from app.services.audio_mixing_engine import audio_mixing_engine, AudioTrackType, DuckingConfig
from app.services.color_pipeline_engine import color_pipeline_engine
from app.services.captions_engine import captions_engine, CaptionStyle
from app.services.motion_graphics_engine import motion_graphics_engine, MotionGraphicType
from app.services.scene_detection_engine import scene_detection_engine
from app.services.ai_editing_command_system import ai_editing_command_system, EditCommandIntent
from app.services.make_auto_edit import make_auto_edit, AutoEditGoal
from app.services.social_versioning_engine import social_versioning_engine, Platform
from app.services.render_engine import render_engine
from app.services.proxy_system import proxy_system
from app.services.post_production_qc import post_production_qc
from app.core.security import get_current_user
from app.models.models import User

router = APIRouter()


@router.post("/timelines/{project_id}/tracks")
async def create_track(project_id: str, track_type: TrackType, name: str, current_user: User = Depends(get_current_user)):
    from app.services.timeline_service import TimelineService
    timeline_service = TimelineService(None)
    timeline = timeline_service.create_timeline(project_id, f"Timeline for {project_id}")
    track = professional_timeline_engine.create_track(timeline, track_type, name)
    return {"track": track}


@router.post("/timelines/{timeline_id}/clips")
async def add_clip(timeline_id: str, clip_id: str, track_id: str, asset_id: str, start_time: float, duration: float, current_user: User = Depends(get_current_user)):
    from app.services.timeline_service import TimelineService
    timeline_service = TimelineService(None)
    timeline = timeline_service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    clip = Clip(
        clip_id=clip_id,
        track_id=track_id,
        asset_id=asset_id,
        start_time=start_time,
        duration=duration,
    )
    result = professional_timeline_engine.add_clip(timeline, clip)
    return {"clip": result}


@router.post("/timelines/{timeline_id}/trim")
async def trim_clip(timeline_id: str, clip_id: str, new_start: float = None, new_duration: float = None, current_user: User = Depends(get_current_user)):
    from app.services.timeline_service import TimelineService
    timeline_service = TimelineService(None)
    timeline = timeline_service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    result = professional_timeline_engine.trim_clip(timeline, clip_id, new_start, new_duration)
    return {"trimmed": result}


@router.post("/timelines/{timeline_id}/split")
async def split_clip(timeline_id: str, clip_id: str, split_time: float, current_user: User = Depends(get_current_user)):
    from app.services.timeline_service import TimelineService
    timeline_service = TimelineService(None)
    timeline = timeline_service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    result = professional_timeline_engine.split_clip(timeline, clip_id, split_time)
    return {"split": result}


@router.post("/timelines/{timeline_id}/transitions")
async def add_transition(timeline_id: str, transition_type: TransitionType, duration: float, from_clip_id: str, to_clip_id: str, current_user: User = Depends(get_current_user)):
    transition = transitions_engine.create_transition(transition_type, duration, from_clip_id, to_clip_id)
    return {"transition": transition.__dict__}


@router.post("/timelines/{timeline_id}/keyframes")
async def add_keyframe(timeline_id: str, clip_id: str, parameter: str, frame: int, value: Any, interpolation: str = "linear", current_user: User = Depends(get_current_user)):
    kf = advanced_keyframe_engine.create_keyframe(clip_id, parameter, frame, value, InterpolationType(interpolation))
    return {"keyframe": kf.__dict__}


@router.post("/editing/interpret")
async def interpret_command(command_text: str, current_user: User = Depends(get_current_user)):
    command = ai_editing_command_system.parse_command(command_text)
    return {
        "command_id": command.command_id,
        "intent": command.intent.value,
        "confidence": command.confidence,
        "parameters": command.parameters,
        "description": command.description,
        "requires_confirmation": command.requires_confirmation,
    }


@router.post("/auto-edit")
async def create_auto_edit(project_id: str, goal: AutoEditGoal, duration_target: float = 60.0, source_asset_ids: List[str] = None, current_user: User = Depends(get_current_user)):
    plan = await make_auto_edit.create_auto_edit_plan(project_id, goal, duration_target, source_asset_ids)
    return {"plan": plan.__dict__}


@router.get("/auto-edit/{plan_id}")
async def get_auto_edit_plan(plan_id: str, current_user: User = Depends(get_current_user)):
    plan = make_auto_edit.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"plan": plan.__dict__}


@router.get("/social-versions")
async def get_social_versions(platforms: List[str] = None, current_user: User = Depends(get_current_user)):
    platform_enums = [Platform(p) for p in (platforms or ["youtube", "instagram_reel", "tiktok"])]
    versions = social_versioning_engine.generate_versions("master", platform_enums)
    return {"versions": versions}


@router.post("/render")
async def render_timeline(timeline_data: Dict[str, Any], output_path: str, fps: int = 30, current_user: User = Depends(get_current_user)):
    result = await render_engine.render_timeline(timeline_data, output_path, fps)
    return result


@router.post("/proxy")
async def create_proxy(source_path: str, proxy_path: str, resolution: tuple = (1280, 720), current_user: User = Depends(get_current_user)):
    result = await render_engine.render_proxy(source_path, proxy_path, resolution)
    return result
