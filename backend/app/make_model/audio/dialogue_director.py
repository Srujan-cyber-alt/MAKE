"""
Dialogue Director - full dialogue reasoning system.

Reasons about: who speaks, why they speak, emotional state,
relationship, previous statements, reaction, interruption, timing, silence.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class RelationshipType(Enum):
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ROMANTIC = "romantic"
    AUTHORITY_SUBORDINATE = "authority_subordinate"
    ADVERSARIAL = "adversarial"
    MENTOR_STUDENT = "mentor_student"
    FAMILY = "family"


class ReactionType(Enum):
    ACKNOWLEDGE = "acknowledge"
    AGREE = "agree"
    DISAGREE = "disagree"
    PROBE = "probe"
    COMFORT = "comfort"
    CHALLENGE = "challenge"
    CONcede = "concede"
    IGNORE = "ignore"


class SpeakingReason(Enum):
    CONTINUE_TOPIC = "continue_topic"
    RESPOND_TO_PROVOCATION = "respond_to_provoke"
    SHARE_INFORMATION = "share_information"
    EXPRESS_EMOTION = "express_emotion"
    MAKE_REQUEST = "make_request"
    GIVE_INSTRUCTION = "give_instruction"
    TELL_JOKE = "tell_joke"
    BREAK_SILENCE = "break_silence"
    INTERJECT = "interject"
    SIGN_OFF = "sign_off"


@dataclass
class SpeakerState:
    speaker_id: str
    current_emotion: Dict[str, float] = field(default_factory=lambda: {
        "happiness": 0.5, "sadness": 0.2, "anger": 0.1, "fear": 0.1,
        "surprise": 0.1, "disgust": 0.05, "calm": 0.6, "excitement": 0.3,
        "confidence": 0.5, "tension": 0.3, "intimacy": 0.2, "urgency": 0.2,
    })
    speaking_rate: float = 1.0
    pitch_offset: float = 0.0
    volume: float = 0.7
    last_spoken: str = ""
    statement_count: int = 0
    emotional_memory: List[Dict[str, float]] = field(default_factory=list)
    dialogue_history: List[str] = field(default_factory=list)
    pending_reaction: Optional[ReactionType] = None
    relationship_to: Dict[str, RelationshipType] = field(default_factory=dict)
    trust_level: float = 0.5
    tension_with: Dict[str, float] = field(default_factory=dict)

    def to_emotion_vector(self) -> np.ndarray:
        emo = self.current_emotion
        return np.array([
            emo.get("happiness", 0), emo.get("sadness", 0), emo.get("anger", 0),
            emo.get("fear", 0), emo.get("surprise", 0), emo.get("disgust", 0),
            emo.get("calm", 0), emo.get("excitement", 0), emo.get("confidence", 0),
            emo.get("tension", 0), emo.get("intimacy", 0), emo.get("urgency", 0),
        ], dtype=np.float32)
    def add_to_history(self, statement: str) -> None:
        self.dialogue_history.append(statement)
        self.last_spoken = statement
        self.statement_count += 1
        self.emotional_memory.append(self.current_emotion.copy())
        if len(self.emotional_memory) > 20:
            self.emotional_memory.pop(0)

    def emotional_drift(self) -> float:
        if len(self.emotional_memory) < 2:
            return 0.0
        diffs = []
        for i in range(1, len(self.emotional_memory)):
            prev = np.array(list(self.emotional_memory[i-1].values()))
            curr = np.array(list(self.emotional_memory[i].values()))
            diffs.append(np.mean(np.abs(curr - prev)))
        return float(np.mean(diffs))

    def detect_emotional_conflict(self) -> bool:
        if not self.emotional_memory:
            return False
        recent = self.emotional_memory[-3:] if len(self.emotional_memory) >= 3 else self.emotional_memory
        avg = np.mean([np.array(list(e.values())) for e in recent], axis=0)
        if avg[2] > 0.7 and avg[0] > 0.7:
            return True
        if avg[3] > 0.7 and avg[6] < 0.2:
            return True
        return False


@dataclass
class DialogueTurn:
    speaker: str
    content: str
    emotion: Dict[str, float]
    timing: float
    reason: SpeakingReason
    reaction_to: Optional[str]
    pause_before: float
    pause_after: float


@dataclass
class SceneContext:
    setting: str
    topic: str
    tension: float
    formality: float
    time_of_day: str
    location: str


class DialogueDirector:
    def __init__(self):
        self.speakers: Dict[str, SpeakerState] = {}
        self.scene_context: Optional[SceneContext] = None
        self.turn_order: List[str] = []
        self.turn_history: List[DialogueTurn] = []
        self.turn_counter = 0

    def add_speaker(self, speaker_id: str, relationship: Dict[str, RelationshipType] = None) -> None:
        self.speakers[speaker_id] = SpeakerState(
            speaker_id=speaker_id,
            relationship_to=relationship or {},
        )

    def set_scene(self, context: SceneContext) -> None:
        self.scene_context = context

    def determine_speaker(self, last_speaker: Optional[str]) -> Optional[str]:
        if len(self.speakers) == 0:
            return None
        if last_speaker is None:
            return list(self.speakers.keys())[0]
        available = [s for s in self.speakers.keys() if s != last_speaker]
        if not available:
            return last_speaker
        if last_speaker in self.speakers:
            state = self.speakers[last_speaker]
            if state.pending_reaction is not None:
                return last_speaker
        return available[0]

    def determine_reason(self, speaker: str, last_content: Optional[str]) -> SpeakingReason:
        if last_content is None:
            return SpeakingReason.BREAK_SILENCE
        state = self.speakers.get(speaker)
        if state and state.pending_reaction:
            return SpeakingReason.RESPOND_TO_PROVOCATION
        if state and state.statement_count == 0:
            return SpeakingReason.CONINUE_TOPIC if hasattr(SpeakingReason, "CONTINUE_TOPIC") else SpeakingReason.CONTINUE_TOPIC
        return SpeakingReason.CONTINUE_TOPIC

    def determine_reaction(self, speaker: str, provocation_speaker: str) -> Optional[ReactionType]:
        if speaker not in self.speakers or provocation_speaker not in self.speakers:
            return None
        spk = self.speakers[speaker]
        prov = self.speakers[provocation_speaker]
        rel = spk.relationship_to.get(provocation_speaker, RelationshipType.NEUTRAL)
        tension = spk.tension_with.get(provocation_speaker, 0.5)

        if rel == RelationshipType.ANTAGONISTIC or tension > 0.7:
            return ReactionType.CHALLENGE
        elif rel == RelationshipType.FRIENDLY:
            return ReactionType.AGREE
        elif rel == RelationshipType.AUTHORITY_SUBORDINATE:
            return ReactionType.CONcede
        else:
            if tension > 0.5:
                return ReactionType.PROBE
            return ReactionType.ACKNOWLEDGE

    def determine_timing(self, speaker: str, last_timing: Optional[float]) -> Tuple[float, float, float]:
        state = self.speakers.get(speaker)
        if state is None:
            return 0.5, 0.3, 1.0
        rate_factor = state.speaking_rate
        base_pause = 0.3 * (1.0 / rate_factor)
        if state.pending_reaction:
            base_pause *= 0.3
        tension = self.scene_context.tension if self.scene_context else 0.5
        pause_before = base_pause * (0.5 + tension)
        pause_after = base_pause * 0.5
        overlap = 0.0
        if tension > 0.7 and state.urgency > 0.5:
            overlap = 0.1 * tension
        return pause_before, pause_after, max(0.1, 1.0 - overlap)

    def determine_interruption(self, current_speaker: str) -> bool:
        if current_speaker not in self.speakers:
            return False
        state = self.speakers[current_speaker]
        if state.current_emotion.get("urgency", 0) > 0.7 and self.scene_context and self.scene_context.tension > 0.6:
            return True
        return False

    def generate_turn(self, content: str, speaker_override: Optional[str] = None) -> DialogueTurn:
        self.turn_counter += 1
        last_speaker = self.turn_history[-1].speaker if self.turn_history else None
        speaker = speaker_override or self.determine_speaker(last_speaker)
        if speaker is None:
            speaker = list(self.speakers.keys())[0] if self.speakers else "default"

        state = self.speakers.get(speaker)
        if state:
            state.add_to_history(content)

        last_content = self.turn_history[-1].content if self.turn_history else None
        reason = self.determine_reason(speaker, last_content)
        last_speaker_prev = self.turn_history[-1].speaker if self.turn_history else None
        reaction = None
        if last_speaker_prev and last_speaker_prev != speaker:
            reaction = self.determine_reaction(speaker, last_speaker_prev)
            if state:
                state.pending_reaction = None

        last_timing = self.turn_history[-1].timing if self.turn_history else None
        pause_before, pause_after, _ = self.determine_timing(speaker, last_timing)

        turn = DialogueTurn(
            speaker=speaker,
            content=content,
            emotion=state.current_emotion.copy() if state else {},
            timing=self.turn_counter * 0.1,
            reason=reason,
            reaction_to=last_speaker_prev,
            pause_before=pause_before,
            pause_after=pause_after,
        )
        self.turn_history.append(turn)
        return turn

    def get_conversational_tension(self) -> float:
        if not self.speakers:
            return 0.0
        tensions = []
        for spk in self.speakers.values():
            for t in spk.tension_with.values():
                tensions.append(t)
        if not tensions:
            return self.scene_context.tension if self.scene_context else 0.5
        return float(np.mean(tensions))

    def get_scene_continuity(self) -> Dict[str, Any]:
        return {
            "total_turns": len(self.turn_history),
            "speakers_active": list(self.speakers.keys()),
            "conversational_tension": self.get_conversational_tension(),
            "scene_tension": self.scene_context.tension if self.scene_context else 0.5,
            "topic": self.scene_context.topic if self.scene_context else "unspecified",
        }

    def export_dialogue(self) -> Dict[str, Any]:
        return {
            "scene": asdict(self.scene_context) if self.scene_context else {},
            "turns": [
                {
                    "speaker": t.speaker,
                    "content": t.content,
                    "emotion": t.emotion,
                    "timing": t.timing,
                    "reason": t.reason.value,
                    "reaction_to": t.reaction_to,
                    "pause_before": t.pause_before,
                    "pause_after": t.pause_after,
                }
                for t in self.turn_history
            ],
            "continuity": self.get_scene_continuity(),
        }
