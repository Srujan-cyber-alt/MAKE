"""
AI Editing Command System for MAKE AI Video Phase 17.

Natural language editing commands mapped to real timeline operations.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class EditCommandIntent(str, Enum):
    TRIM = "trim"
    CUT = "cut"
    SPLIT = "split"
    DELETE = "delete"
    MOVE = "move"
    REORDER = "reorder"
    SPEED = "speed"
    CROP = "crop"
    DUPLICATE = "duplicate"
    FREEZE = "freeze"
    REVERSE = "reverse"
    TRANSITION = "transition"
    COLOR = "color"
    AUDIO = "audio"
    CAPTION = "caption"
    BROLL = "broll"
    REMOVE_BACKGROUND = "remove_background"
    REPLACE_BACKGROUND = "replace_background"
    OBJECT_REMOVAL = "object_removal"
    BLUR = "blur"
    STABILIZE = "stabilize"
    REFRAME = "reframe"
    EXPORT = "export"
    UNKNOWN = "unknown"


@dataclass
class EditCommand:
    command_id: str
    intent: EditCommandIntent
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    description: str = ""
    requires_confirmation: bool = False


class AIEditingCommandSystem:
    INTENT_PATTERNS = {
        EditCommandIntent.TRIM: [r"trim\s+(?:the\s+)?(?:first|last)\s+(\d+)\s*(?:second|sec|s)", r"cut\s+(?:the\s+)?(?:first|last)\s+(\d+)"],
        EditCommandIntent.CUT: [r"cut\s+(?:out|remove|delete)\s+(.+)"],
        EditCommandIntent.SPEED: [r"(\d+%?\s*(?:faster|slower))", r"speed\s+(?:up|down)?\s*(\d+%?)", r"(\d+x)\s*speed"],
        EditCommandIntent.DELETE: [r"remove\s+(?:the\s+)?(?:first|last)?\s*(\d+)?\s*(?:second|sec|s)?", r"delete\s+(.+)"],
        EditCommandIntent.MOVE: [r"move\s+(.+?)\s+(?:before|after|to)\s+(.+)"],
        EditCommandIntent.REORDER: [r"put\s+(.+?)\s+(?:before|after)\s+(.+)"],
        EditCommandIntent.COLOR: [r"make\s+(?:it\s+)?(warmer|cooler|brighter|darker|more\s+cinematic)", r"color\s+(?:match|grade|correct)\s+(.+)"],
        EditCommandIntent.CAPTION: [r"add\s+captions?", r"remove\s+(?:filler|uh|um)", r"make\s+subtitles?\s+(bigger|smaller)"],
        EditCommandIntent.BROLL: [r"add\s+b-roll", r"insert\s+b\s*roll"],
        EditCommandIntent.REMOVE_BACKGROUND: [r"remove\s+(?:the\s+)?background", r"replace\s+(?:the\s+)?background"],
        EditCommandIntent.STABILIZE: [r"stabilize\s+(?:this|the\s+video|clip)"],
        EditCommandIntent.REFRAME: [r"reframe\s+(?:to\s+)?(\d+:\d+)", r"make\s+(?:it\s+)?(vertical|horizontal|square)"],
        EditCommandIntent.EXPORT: [r"export\s+(?:for\s+)?(.+)", r"render\s+(?:for\s+)?(.+)"],
    }

    def parse_command(self, command_text: str, context: Dict[str, Any] = None) -> EditCommand:
        import uuid
        command_text = command_text.lower().strip()
        context = context or {}
        best_intent = EditCommandIntent.UNKNOWN
        best_confidence = 0.0
        best_params = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, command_text)
                if match:
                    confidence = 0.8 if match.group(0) else 0.0
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
                        best_params = {"match": match.group(0), "groups": match.groups()}
        if best_intent == EditCommandIntent.UNKNOWN:
            best_confidence = 0.3
        requires_confirmation = best_intent in (
            EditCommandIntent.DELETE, EditCommandIntent.REMOVE_BACKGROUND, EditCommandIntent.REPLACE_BACKGROUND,
            EditCommandIntent.EXPORT, EditCommandIntent.BROLL,
        )
        return EditCommand(
            command_id=str(uuid.uuid4()),
            intent=best_intent,
            parameters=best_params,
            confidence=best_confidence,
            description=command_text,
            requires_confirmation=requires_confirmation,
        )

    def generate_edit_plan_from_commands(self, commands: List[EditCommand]) -> Dict[str, Any]:
        return {
            "plan_id": str(__import__("uuid").uuid4()),
            "commands": [c.__dict__ for c in commands],
            "total_operations": len(commands),
            "requires_confirmation": any(c.requires_confirmation for c in commands),
        }


ai_editing_command_system = AIEditingCommandSystem()
