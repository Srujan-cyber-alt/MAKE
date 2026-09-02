"""
Generation Reality Layer for MAKE AI Video Phase 19.

Wraps every generation attempt with structured observability state.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class GenerationRealityLayer:
    @staticmethod
    def create_generation_event(shot_id: str, project_id: str, scene_id: str, model: str, provider: str, prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "generation_id": str(uuid.uuid4()),
            "project_id": project_id,
            "scene_id": scene_id,
            "shot_id": shot_id,
            "model": model,
            "provider": provider,
            "prompt": prompt,
            "parameters": parameters,
            "status": "started",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "duration": None,
            "result": None,
            "technical_validation": None,
            "visual_analysis": None,
            "quality_score": None,
            "continuity_score": None,
            "failure_analysis": None,
            "repair_attempts": [],
            "variant_group": None,
            "final_selection": None,
            "cost": None,
        }
        return event

    @staticmethod
    def mark_completed(event: Dict[str, Any], result: Dict[str, Any], cost: Optional[float] = None) -> Dict[str, Any]:
        event["status"] = "completed"
        event["completed_at"] = datetime.utcnow().isoformat()
        event["result"] = result
        event["cost"] = cost
        started = datetime.fromisoformat(event["started_at"])
        event["duration"] = (datetime.utcnow() - started).total_seconds()
        return event

    @staticmethod
    def mark_failed(event: Dict[str, Any], failure: Dict[str, Any]) -> Dict[str, Any]:
        event["status"] = "failed"
        event["completed_at"] = datetime.utcnow().isoformat()
        event["failure_analysis"] = failure
        started = datetime.fromisoformat(event["started_at"])
        event["duration"] = (datetime.utcnow() - started).total_seconds()
        return event

    @staticmethod
    def add_repair_attempt(event: Dict[str, Any], repair: Dict[str, Any]) -> Dict[str, Any]:
        event.setdefault("repair_attempts", []).append(repair)
        event["repair_count"] = len(event["repair_attempts"])
        return event

    @staticmethod
    def attach_scores(event: Dict[str, Any], technical: Dict[str, Any], visual: Dict[str, Any], quality: Dict[str, Any], continuity: Dict[str, Any]) -> Dict[str, Any]:
        event["technical_validation"] = technical
        event["visual_analysis"] = visual
        event["quality_score"] = quality
        event["continuity_score"] = continuity
        event["overall_score"] = quality.get("overall", 0.0)
        return event


generation_reality_layer = GenerationRealityLayer()
