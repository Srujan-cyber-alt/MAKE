"""
Semantic audio editor.

Translates high-level commands ("remove horn", "make angrier", "extend silence")
into concrete audio operations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SemanticCommand(str, Enum):
    REMOVE_SOURCE = "remove_source"
    CHANGE_EMOTION = "change_emotion"
    EXTEND_SILENCE = "extend_silence"
    ADJUST_TEMPO = "adjust_tempo"
    CHANGE_PITCH = "change_pitch"
    REMOVE_REVERB = "remove_reverb"
    NORMALIZE = "normalize"
    MUTE_REGION = "mute_region"
    REPLACE_WORD = "replace_word"
    ADD_PAUSES = "add_pauses"


@dataclass
class SemanticEdit:
    command: SemanticCommand
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_region: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command.value,
            "parameters": dict(self.parameters),
            "target_region": list(self.target_region) if self.target_region else None,
        }


class SemanticEditor:
    """Parse natural-language commands into audio edits."""

    PATTERNS: Dict[SemanticCommand, List[str]] = {
        SemanticCommand.REMOVE_SOURCE: [r"remove\s+(?:the\s+)?(\w+)", r"mute\s+(?:the\s+)?(\w+)"],
        SemanticCommand.CHANGE_EMOTION: [r"make\s+(?:the\s+)?(?:voice\s+)?(\w+)\s*(?:angry|angrier|sad|happy|calm)", r"make\s+(\w+)\s*(?:angry|angrier|sad|happy|calm)"],
        SemanticCommand.EXTEND_SILENCE: [r"extend\s+silence", r"lengthen\s+silence"],
        SemanticCommand.ADJUST_TEMPO: [r"slow\s+down", r"speed\s+up", r"tempo\s*([0-9.]+)"],
        SemanticCommand.CHANGE_PITCH: [r"pitch\s*(up|down)\s*([0-9.]+)", r"shift\s+pitch"],
        SemanticCommand.REMOVE_REVERB: [r"remove\s+reverb", r"dry\s+the\s+audio"],
        SemanticCommand.NORMALIZE: [r"normalize", r"adjust\s+volume"],
        SemanticCommand.MUTE_REGION: [r"mute\s+from\s+([0-9.]+)\s+to\s+([0-9.]+)"],
        SemanticCommand.REPLACE_WORD: [r"replace\s+(\w+)\s+with\s+(.+)"],
        SemanticCommand.ADD_PAUSES: [r"add\s+pause", r"insert\s+pause"],
    }

    # Check MUTE_REGION before the generic REMOVE_SOURCE "mute <word>" pattern.
    PATTERN_ORDER = [
        SemanticCommand.MUTE_REGION,
        SemanticCommand.REMOVE_SOURCE,
        SemanticCommand.CHANGE_EMOTION,
        SemanticCommand.EXTEND_SILENCE,
        SemanticCommand.ADJUST_TEMPO,
        SemanticCommand.CHANGE_PITCH,
        SemanticCommand.REMOVE_REVERB,
        SemanticCommand.NORMALIZE,
        SemanticCommand.REPLACE_WORD,
        SemanticCommand.ADD_PAUSES,
    ]

    def __init__(self) -> None:
        self._compiled = {cmd: [re.compile(p, re.IGNORECASE) for p in pats] for cmd, pats in self.PATTERNS.items()}

    def parse(self, text: str) -> List[SemanticEdit]:
        edits: List[SemanticEdit] = []
        for cmd in self.PATTERN_ORDER:
            patterns = self._compiled[cmd]
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    params: Dict[str, Any] = {}
                    target_region: Optional[Tuple[float, float]] = None
                    if cmd == SemanticCommand.REMOVE_SOURCE:
                        params["source"] = match.group(1)
                    elif cmd == SemanticCommand.CHANGE_EMOTION:
                        params["target"] = match.group(1)
                        params["emotion"] = match.group(0).split()[-1].lower()
                    elif cmd == SemanticCommand.ADJUST_TEMPO:
                        if match.lastindex and match.lastindex >= 1:
                            params["factor"] = float(match.group(1))
                        else:
                            params["factor"] = 0.9 if "slow" in text.lower() else 1.1
                    elif cmd == SemanticCommand.CHANGE_PITCH:
                        direction = match.group(1) if match.lastindex and match.lastindex >= 1 else "up"
                        amount = float(match.group(2)) if match.lastindex and match.lastindex >= 2 else 1.0
                        params["direction"] = direction
                        params["semitones"] = amount
                    elif cmd == SemanticCommand.MUTE_REGION:
                        target_region = (float(match.group(1)), float(match.group(2)))
                    elif cmd == SemanticCommand.REPLACE_WORD:
                        params["old"] = match.group(1)
                        params["new"] = match.group(2).strip()
                    edits.append(SemanticEdit(command=cmd, parameters=params, target_region=target_region))
        return edits

    def apply(self, audio: np.ndarray, edit: SemanticEdit, sample_rate: int = 16000) -> np.ndarray:
        """Apply a single edit to ``audio`` and return the result."""
        result = audio.copy()
        cmd = edit.command
        if cmd == SemanticCommand.MUTE_REGION and edit.target_region:
            start = int(edit.target_region[0] * sample_rate)
            end = int(edit.target_region[1] * sample_rate)
            if result.ndim > 1:
                result[max(0, start):end] = 0.0
            else:
                result[max(0, start):end] = 0.0
        elif cmd == SemanticCommand.EXTEND_SILENCE:
            pad = int(edit.parameters.get("duration", 1.0) * sample_rate)
            silence = np.zeros(pad, dtype=result.dtype)
            if result.ndim > 1:
                silence = np.broadcast_to(silence[:, None], (pad, result.shape[1])).copy()
            result = np.concatenate([result, silence])
        elif cmd == SemanticCommand.NORMALIZE:
            peak = float(np.max(np.abs(result))) if result.size else 1.0
            if peak > 0:
                result = result / peak * 0.95
        return result

    def apply_batch(self, audio: np.ndarray, edits: List[SemanticEdit], sample_rate: int = 16000) -> np.ndarray:
        result = audio
        for edit in edits:
            result = self.apply(result, edit, sample_rate=sample_rate)
        return result