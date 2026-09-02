"""
Repair Planner for MAKE AI Video Phase 19.

Generates repair strategies for failed generations.
"""

from typing import Optional, List, Dict, Any
from app.services.failure_classifier import failure_classifier, GenerationFailureType
from app.services.model_router_4 import model_router_4, RoutingMode
from app.services.advanced_prompt_compiler import AdvancedPromptCompiler
from app.schemas.phase9 import CinematicPromptCompilation
import logging

logger = logging.getLogger(__name__)


class RepairStrategy:
    RETRY_SAME_MODEL = "retry_same_model"
    CHANGE_MODEL = "change_model"
    CHANGE_PROVIDER = "change_provider"
    CHANGE_PROMPT = "change_prompt"
    ADD_REFERENCE = "add_reference"
    CHANGE_REFERENCE = "change_reference"
    CHANGE_CAMERA = "change_camera"
    CHANGE_DURATION = "change_duration"
    CHANGE_RESOLUTION = "change_resolution"
    V2V_REPAIR = "v2v_repair"
    FRAME_REPAIR = "frame_repair"
    FULL_REGENERATION = "full_regeneration"
    MANUAL_REVIEW = "manual_review"


class RepairPlanner:
    @staticmethod
    def plan(failure_type: GenerationFailureType, severity: str, shot: Dict[str, Any], context: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        strategy = {
            "failure_type": failure_type.value,
            "severity": severity,
            "retry_count": retry_count,
            "recommended_strategy": RepairPlanner._select_strategy(failure_type, severity, retry_count),
            "actions": [],
            "parameters": {},
        }

        if strategy["recommended_strategy"] == RepairStrategy.CHANGE_PROMPT:
            strategy["actions"].append("improve_prompt")
            strategy["parameters"]["compiled_prompt"] = AdvancedPromptCompiler.compile_from_prompt(shot.get("description", ""), context)
        elif strategy["recommended_strategy"] == RepairStrategy.CHANGE_MODEL:
            strategy["actions"].append("reroute_model")
            strategy["parameters"]["routing_mode"] = RoutingMode.AUTO.value
        elif strategy["recommended_strategy"] == RepairStrategy.ADD_REFERENCE:
            strategy["actions"].append("attach_references")
            strategy["parameters"]["reference_types"] = ["character", "product"]
        elif strategy["recommended_strategy"] == RepairStrategy.FULL_REGENERATION:
            strategy["actions"].append("full_regeneration")

        return strategy

    @staticmethod
    def _select_strategy(failure_type: GenerationFailureType, severity: str, retry_count: int) -> str:
        if retry_count >= 3:
            return RepairStrategy.MANUAL_REVIEW
        if severity == "critical":
            return RepairStrategy.FULL_REGENERATION
        if failure_type == GenerationFailureType.IDENTITY_FAILURE:
            return RepairStrategy.ADD_REFERENCE
        if failure_type == GenerationFailureType.PRODUCT_FAILURE:
            return RepairStrategy.ADD_REFERENCE
        if failure_type == GenerationFailureType.TEMPORAL_FAILURE:
            return RepairStrategy.CHANGE_MODEL
        if failure_type == GenerationFailureType.QUALITY_FAILURE:
            return RepairStrategy.CHANGE_MODEL
        return RepairStrategy.CHANGE_PROMPT


repair_planner = RepairPlanner()
