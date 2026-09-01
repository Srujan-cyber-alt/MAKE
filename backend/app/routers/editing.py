from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.schemas.schemas import CommandInterpretRequest, CommandInterpretResponse
from app.models.models import Job, JobType, JobStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
import re

router = APIRouter()


class AICommandInterpreter:
    def interpret(self, command: str, context: Optional[dict] = None) -> CommandInterpretResponse:
        command_lower = command.lower().strip()
        operations = []
        confidence = 0.8
        clarification_questions = []

        if "remove" in command_lower and ("person" in command_lower or "people" in command_lower or "guy" in command_lower or "man" in command_lower):
            operations.append({
                "operation": "object_removal",
                "target": "person",
                "method": "inpainting",
                "tracking": "automatic",
            })
            confidence = 0.85
        elif "remove" in command_lower and ("car" in command_lower or "object" in command_lower):
            operations.append({
                "operation": "object_removal",
                "target": "object",
                "method": "inpainting",
                "tracking": "automatic",
            })
            confidence = 0.85
        elif "replace" in command_lower and "background" in command_lower:
            operations.append({
                "operation": "background_replacement",
                "target": "background",
                "method": "segmentation",
            })
            confidence = 0.9
        elif "make" in command_lower and "black" in command_lower and "car" in command_lower:
            operations.append({
                "operation": "object_recoloring",
                "target": "car",
                "color": "black",
                "preserve_lighting": True,
            })
            confidence = 0.85
        elif "make" in command_lower and any(action in command_lower for action in ["walk", "run", "jump", "sit", "drive", "open", "pick"]):
            actions = ["walk", "run", "jump", "sit", "drive", "open", "pick"]
            action = next(a for a in actions if a in command_lower)
            operations.append({
                "operation": "action_transformation",
                "target": "character",
                "new_action": action,
                "preserve_identity": True,
                "preserve_environment": True,
            })
            confidence = 0.75
            clarification_questions.append("Which character should perform this action?")
        elif "trim" in command_lower or "cut" in command_lower:
            operations.append({
                "operation": "trim",
                "method": "natural_language",
            })
            confidence = 0.9
        elif "caption" in command_lower or "subtitles" in command_lower:
            operations.append({
                "operation": "add_captions",
                "style": "auto",
            })
            confidence = 0.9
        elif "extend" in command_lower or "longer" in command_lower:
            operations.append({
                "operation": "video_extension",
                "preserve_continuity": True,
            })
            confidence = 0.85
        elif "slow motion" in command_lower or "slow-mo" in command_lower:
            operations.append({
                "operation": "speed_adjustment",
                "speed": 0.25,
            })
            confidence = 0.9
        elif "cinematic" in command_lower:
            operations.append({
                "operation": "style_transfer",
                "style": "cinematic",
                "preserve_motion": True,
            })
            confidence = 0.8
        elif "crop" in command_lower or "aspect" in command_lower:
            aspect_match = re.search(r"(\d+):(\d+)", command)
            aspect_ratio = aspect_match.group(0) if aspect_match else "16:9"
            operations.append({
                "operation": "aspect_ratio_change",
                "aspect_ratio": aspect_ratio,
            })
            confidence = 0.9
        elif "color" in command_lower or "colour" in command_lower:
            operations.append({
                "operation": "color_adjustment",
                "method": "ai_assisted",
            })
            confidence = 0.7
            clarification_questions.append("What specific color changes would you like?")
        else:
            operations.append({
                "operation": "general_transform",
                "instruction": command,
                "method": "text_to_video_edit",
            })
            confidence = 0.5
            clarification_questions.append("Could you provide more details about the desired edit?")

        requires_clarification = len(clarification_questions) > 0 or confidence < 0.8

        return CommandInterpretResponse(
            operations=operations,
            confidence=confidence,
            requires_clarification=requires_clarification,
            clarification_questions=clarification_questions or None,
        )


interpreter = AICommandInterpreter()


@router.post("/interpret", response_model=CommandInterpretResponse)
async def interpret_command(request: CommandInterpretRequest):
    return interpreter.interpret(request.command, request.context)


@router.post("/execute")
async def execute_command(
    request: CommandInterpretRequest,
    project_id: str = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = interpreter.interpret(request.command, request.context)

    job = Job(
        user_id=current_user.id,
        project_id=project_id,
        job_type=JobType.EDIT,
        prompt=request.command,
        parameters={"operations": result.operations, "confidence": result.confidence},
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"job_id": job.id, "interpretation": result}
