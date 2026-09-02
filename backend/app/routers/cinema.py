"""
Phase 18 Cinema & Generative Production API Router.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Project
from app.services.production_engine import production_engine, ProductionGoal, ProductionStatus
from app.services.production_graph import production_graph, NodeStatus
from app.services.make_auto_cinema import make_auto_cinema
from app.services.production_templates import production_templates
from app.services.approval_gate import approval_gate
from app.services.cinematic_quality_score import cinematic_quality_score
from app.services.continuity_engine import continuity_engine
from app.services.shot_generation_planner import shot_generation_planner

router = APIRouter()


@router.post("/projects/{project_id}/cinema/auto")
async def auto_cinema(
    project_id: str,
    brief: Dict[str, Any],
    goal: str = ProductionGoal.COMMERCIAL,
    mode: str = "balanced",
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await make_auto_cinema.execute(
        user_id=current_user.id,
        project_id=project_id,
        brief=brief,
        goal=goal,
        mode=mode,
        template_id=template_id,
    )
    return result


@router.get("/templates")
async def list_templates(current_user: User = Depends(get_current_user)):
    return {"templates": production_templates.list_templates()}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, current_user: User = Depends(get_current_user)):
    template = production_templates.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/projects/{project_id}/cinema/approve")
async def approve_stage(
    project_id: str,
    stage: str,
    notes: str = None,
    current_user: User = Depends(get_current_user),
):
    gate = approval_gate.create_gate(project_id, stage)
    approved = approval_gate.approve(gate, current_user.id, notes)
    return approved


@router.post("/projects/{project_id}/cinema/reject")
async def reject_stage(
    project_id: str,
    stage: str,
    notes: str = None,
    current_user: User = Depends(get_current_user),
):
    gate = approval_gate.create_gate(project_id, stage)
    rejected = approval_gate.reject(gate, current_user.id, notes)
    return rejected


@router.get("/projects/{project_id}/cinema/continuity")
async def get_continuity(project_id: str, current_user: User = Depends(get_current_user)):
    shots = []
    continuity = continuity_engine.validate_shot_continuity(shots, {})
    return continuity


@router.post("/projects/{project_id}/cinema/quality")
async def score_quality(project_id: str, production: Dict[str, Any], current_user: User = Depends(get_current_user)):
    score = cinematic_quality_score.score_production(production)
    return score


@router.post("/projects/{project_id}/cinema/shot-plan")
async def create_shot_plan(
    project_id: str,
    shot: Dict[str, Any],
    production_context: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
):
    plan = shot_generation_planner.create_shot_plan(shot, production_context or {})
    return plan
