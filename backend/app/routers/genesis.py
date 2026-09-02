"""
Phase 19 Genesis & Generation Quality API Router.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Project
from app.services.genesis_engine import make_genesis
from app.services.shot_intelligence import shot_intelligence
from app.services.reference_intelligence import reference_intelligence
from app.services.artifact_detector import artifact_detector
from app.services.cinematic_quality_score import cinematic_quality_score
from app.services.technical_validator import technical_validator
from app.services.production_templates import production_templates

router = APIRouter()


@router.post("/projects/{project_id}/genesis/auto")
async def genesis_auto(
    project_id: str,
    brief: Dict[str, Any],
    goal: str = "commercial",
    mode: str = "balanced",
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await make_genesis.execute(
        user_id=current_user.id,
        project_id=project_id,
        brief=brief,
        goal=goal,
        mode=mode,
        template_id=template_id,
    )
    return result


@router.post("/projects/{project_id}/genesis/shot-intelligence")
async def shot_intelligence_endpoint(
    project_id: str,
    shot: Dict[str, Any],
    context: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
):
    result = shot_intelligence.evaluate(shot, context or {})
    return result


@router.post("/projects/{project_id}/genesis/references/classify")
async def classify_references(
    project_id: str,
    references: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
):
    classified = reference_intelligence.classify(references)
    conflicts = reference_intelligence.detect_conflicts(references)
    return {"classified": classified, "conflicts": conflicts}


@router.post("/projects/{project_id}/genesis/artifacts/detect")
async def detect_artifacts(
    project_id: str,
    analysis: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    artifacts = artifact_detector.classify(analysis)
    return {"artifacts": artifacts, "total": len(artifacts)}


@router.post("/projects/{project_id}/genesis/quality/score")
async def genesis_quality_score(
    project_id: str,
    production: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    score = cinematic_quality_score.score_production(production)
    return score


@router.post("/projects/{project_id}/genesis/technical/validate")
async def genesis_technical_validate(
    project_id: str,
    video_path: str,
    current_user: User = Depends(get_current_user),
):
    result = await technical_validator.validate(video_path)
    return result
