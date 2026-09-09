"""
Audio reasoning: connect user intent to an audio plan.

Parses natural-language intent and routes it to the appropriate audio
subsystem (voice, emotion, dialogue, foley, spatial, music, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.sound_director import SoundDirector, AudioPlan


class IntentType(str, Enum):
    GENERATE_VOICE = "generate_voice"
    GENERATE_DIALOGUE = "generate_dialogue"
    GENERATE_MUSIC = "generate_music"
    GENERATE_FOLEY = "generate_foley"
    GENERATE_SOUNDSCAPE = "generate_soundscape"
    APPLY_EMOTION = "apply_emotion"
    APPLY_SPATIAL = "apply_spatial"
    APPLY_ACOUSTICS = "apply_acoustics"
    EDIT_AUDIO = "edit_audio"
    REPAIR_AUDIO = "repair_audio"
    MIX_AUDIO = "mix_audio"


@dataclass
class AudioIntent:
    intent_type: IntentType
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "parameters": dict(self.parameters),
            "confidence": self.confidence,
            "raw_text": self.raw_text,
        }


INTENT_PATTERNS: List[Tuple[IntentType, List[str]]] = [
    (IntentType.GENERATE_VOICE, [r"generate\s+voice", r"speak\s+text", r"synthesize\s+speech"]),
    (IntentType.GENERATE_DIALOGUE, [r"dialogue", r"conversation", r"multi\s*speaker"]),
    (IntentType.GENERATE_MUSIC, [r"generate\s+music", r"compose", r"create\s+a\s+song"]),
    (IntentType.GENERATE_FOLEY, [r"foley", r"footstep", r"door\s+creak", r"impact"]),
    (IntentType.GENERATE_SOUNDSCAPE, [r"soundscape", r"ambience", r"environment"]),
    (IntentType.APPLY_EMOTION, [r"emotion", r"make\s+\w+", r"angry", r"sad", r"happy"]),
    (IntentType.APPLY_SPATIAL, [r"spatial", r"position", r"pan", r"3d"]),
    (IntentType.APPLY_ACOUSTICS, [r"acoustics", r"reverb", r"room", r"hall"]),
    (IntentType.EDIT_AUDIO, [r"edit", r"trim", r"cut", r"replace"]),
    (IntentType.REPAIR_AUDIO, [r"repair", r"denoise", r"remove\s+noise", r"declipping"]),
    (IntentType.MIX_AUDIO, [r"mix", r"blend", r"duck"]),
]


class AudioReasoning:
    """Connect user intent to an audio plan."""

    def __init__(self, director: Optional[SoundDirector] = None) -> None:
        self.director = director or SoundDirector()
        self._compiled = [(it, [re.compile(p, re.IGNORECASE) for p in pats]) for it, pats in INTENT_PATTERNS]

    def parse_intent(self, text: str) -> AudioIntent:
        best_intent: Optional[AudioIntent] = None
        best_matches = 0
        for intent_type, patterns in self._compiled:
            matches = 0
            for pattern in patterns:
                if pattern.search(text):
                    matches += 1
            if matches > best_matches:
                best_matches = matches
                parameters = self._extract_parameters(text, intent_type)
                confidence = min(1.0, 0.3 + 0.1 * matches)
                best_intent = AudioIntent(
                    intent_type=intent_type,
                    parameters=parameters,
                    confidence=confidence,
                    raw_text=text,
                )
        if best_intent is None:
            best_intent = AudioIntent(intent_type=IntentType.GENERATE_VOICE, raw_text=text, confidence=0.3)
        return best_intent

    def _extract_parameters(self, text: str, intent_type: IntentType) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        # Extract quoted strings.
        quotes = re.findall(r'"([^"]+)"', text)
        if quotes:
            params["text"] = quotes[0]
        # Extract numbers.
        numbers = re.findall(r"([0-9]+(?:\.[0-9]+)?)", text)
        if numbers:
            try:
                params["duration"] = float(numbers[0])
            except ValueError:
                pass
        return params

    def route(self, intent: AudioIntent) -> Dict[str, Any]:
        """Return a routing descriptor for the intent."""
        return {
            "intent": intent.to_dict(),
            "handler": intent.intent_type.value,
            "director_available": self.director is not None,
        }