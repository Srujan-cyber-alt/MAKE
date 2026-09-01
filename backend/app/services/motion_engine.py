from typing import Optional, List, Dict, Any
from app.schemas.phase9 import MotionDefinition
import logging

logger = logging.getLogger(__name__)


class MotionEngine:
    ACTION_KEYWORDS = {
        "walk": "walk",
        "run": "run",
        "jump": "jump",
        "dance": "dance",
        "turn": "turn",
        "sit": "sit",
        "stand": "stand",
        "gesture": "gesture",
        "fight": "fight",
        "throw": "throw",
        "catch": "catch",
        "interact": "interact",
        "pick up": "pick_up",
        "open": "open",
        "close": "close",
        "pour": "pour",
        "drive": "drive",
        "ride": "ride",
        "look": "look",
        "talk": "talk",
        "smile": "smile",
        "cry": "cry",
    }

    @staticmethod
    def parse_natural_language(prompt: str) -> List[MotionDefinition]:
        prompt_lower = prompt.lower()
        motions = []

        for keyword, action in MotionEngine.ACTION_KEYWORDS.items():
            if keyword in prompt_lower:
                motion = MotionDefinition(
                    action=action,
                    intensity=1.0,
                    physically_plausible=True,
                )
                if "slow" in prompt_lower:
                    motion.intensity = 0.5
                if "fast" in prompt_lower or "quickly" in prompt_lower:
                    motion.intensity = 1.5
                motions.append(motion)

        if not motions:
            motions.append(MotionDefinition(action="idle", intensity=0.0, physically_plausible=True))

        return motions

    @staticmethod
    def to_generation_parameters(motions: List[MotionDefinition]) -> Dict[str, Any]:
        if not motions:
            return {}
        primary = motions[0]
        return {
            "motion_action": primary.action,
            "motion_intensity": primary.intensity,
            "physically_plausible": primary.physically_plausible,
            "subject": primary.subject,
            "object": primary.object,
            "relationship": primary.relationship,
        }
