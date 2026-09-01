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
        "fall": "fall",
        "swim": "swim",
        "fly": "fly",
        "grab": "grab",
        "push": "push",
        "pull": "pull",
        "facial expression": "facial_expression",
    }

    SPEED_KEYWORDS = {
        "slowly": 0.4,
        "slow": 0.5,
        "moderate": 0.7,
        "fast": 1.2,
        "quickly": 1.3,
        "rapidly": 1.5,
    }

    @staticmethod
    def parse_natural_language(prompt: str) -> List[MotionDefinition]:
        prompt_lower = prompt.lower()
        motions = []

        for keyword, action in MotionEngine.ACTION_KEYWORDS.items():
            if keyword in prompt_lower:
                motion = MotionDefinition(
                    action=action,
                    intensity=MotionEngine._parse_intensity(prompt_lower),
                    speed=MotionEngine._parse_speed(prompt_lower),
                    direction=MotionEngine._parse_direction(prompt_lower),
                    trajectory=MotionEngine._parse_trajectory(prompt_lower),
                    timing=MotionEngine._parse_timing(prompt_lower),
                    acceleration=MotionEngine._parse_acceleration(prompt_lower),
                    deceleration=MotionEngine._parse_deceleration(prompt_lower),
                    physically_plausible=MotionEngine._validate_physical_plausibility(action, prompt_lower),
                )
                motions.append(motion)

        if not motions:
            motions.append(MotionDefinition(
                action="idle",
                intensity=0.0,
                speed=1.0,
                direction="none",
                trajectory="linear",
                timing="immediate",
                acceleration="none",
                deceleration="none",
                physically_plausible=True,
            ))

        return motions

    @staticmethod
    def _parse_intensity(prompt_lower: str) -> float:
        if "subtle" in prompt_lower or "gentle" in prompt_lower:
            return 0.3
        if "intense" in prompt_lower or "powerful" in prompt_lower:
            return 1.5
        if "slowly" in prompt_lower:
            return 0.5
        if "fast" in prompt_lower or "quickly" in prompt_lower:
            return 1.2
        return 0.8

    @staticmethod
    def _parse_speed(prompt_lower: str) -> float:
        for keyword, speed in MotionEngine.SPEED_KEYWORDS.items():
            if keyword in prompt_lower:
                return speed
        return 1.0

    @staticmethod
    def _parse_direction(prompt_lower: str) -> str:
        if "left" in prompt_lower:
            return "left"
        if "right" in prompt_lower:
            return "right"
        if "forward" in prompt_lower or "toward" in prompt_lower:
            return "forward"
        if "backward" in prompt_lower or "away" in prompt_lower:
            return "backward"
        if "up" in prompt_lower:
            return "up"
        if "down" in prompt_lower:
            return "down"
        return "center"

    @staticmethod
    def _parse_trajectory(prompt_lower: str) -> str:
        if "circle" in prompt_lower or "orbit" in prompt_lower:
            return "circular"
        if "arc" in prompt_lower:
            return "arc"
        if "zigzag" in prompt_lower:
            return "zigzag"
        if "straight" in prompt_lower:
            return "linear"
        return "linear"

    @staticmethod
    def _parse_timing(prompt_lower: str) -> str:
        if "slowly" in prompt_lower or "gradual" in prompt_lower:
            return "gradual"
        if "sudden" in prompt_lower or "instantly" in prompt_lower:
            return "sudden"
        return "natural"

    @staticmethod
    def _parse_acceleration(prompt_lower: str) -> str:
        if "smooth" in prompt_lower or "gradual" in prompt_lower:
            return "smooth"
        if "sudden" in prompt_lower:
            return "sudden"
        return "natural"

    @staticmethod
    def _parse_deceleration(prompt_lower: str) -> str:
        if "smooth" in prompt_lower or "gradual" in prompt_lower:
            return "smooth"
        if "sudden" in prompt_lower or "abrupt" in prompt_lower:
            return "sudden"
        return "natural"

    @staticmethod
    def _validate_physical_plausibility(action: str, prompt_lower: str) -> bool:
        impossible = ["walk on water", "fly without wings", "float in space"]
        for phrase in impossible:
            if phrase in prompt_lower:
                return False
        return True

    @staticmethod
    def to_generation_parameters(motions: List[MotionDefinition]) -> Dict[str, Any]:
        if not motions:
            return {}
        primary = motions[0]
        return {
            "motion_action": primary.action,
            "motion_intensity": primary.intensity,
            "motion_speed": primary.speed,
            "motion_direction": primary.direction,
            "motion_trajectory": primary.trajectory,
            "motion_timing": primary.timing,
            "motion_acceleration": primary.acceleration,
            "motion_deceleration": primary.deceleration,
            "physically_plausible": primary.physically_plausible,
            "subject": primary.subject,
            "object": primary.object,
            "relationship": primary.relationship,
        }
