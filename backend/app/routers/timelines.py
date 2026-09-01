from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Project, Timeline
from app.schemas.schemas import TimelineCreate, TimelineResponse

router = APIRouter()


@router.post("/{project_id}/timelines", response_model=TimelineResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/{project_id}/timelines", response_model=list[TimelineResponse])
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


@router.get("/{timeline_id}", response_model=TimelineResponse)
async def get_timeline(
    timeline_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Timeline).where(Timeline.id == timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    return timeline


@router.patch("/{timeline_id}", response_model=TimelineResponse)
async def update_timeline(
    timeline_id: str,
    timeline_data: TimelineCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Timeline).where(Timeline.id == timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")

    timeline.name = timeline_data.name
    timeline.duration_seconds = timeline_data.duration_seconds
    timeline.fps = timeline_data.fps
    timeline.resolution = timeline_data.resolution
    timeline.tracks = timeline_data.tracks
    timeline.settings = timeline_data.settings
    await db.commit()
    await db.refresh(timeline)
    return timeline


@router.delete("/{timeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timeline(
    timeline_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Timeline).where(Timeline.id == timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")
    await db.delete(timeline)
    await db.commit()
