"""
Sound director: high-level scene-to-audio-plan generator.

Translates a scene description into a concrete audio plan with sources,
effects, and mixing instructions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.dialogue_scene import DialogueScene
from app.make_model.audio.audio_world import AudioWorld


class AudioPlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    RENDERED = "rendered"


@dataclass
class AudioSource:
    source_id: str
    source_type: str  # dialogue | foley | ambience | music | effect
    start_time: float
    duration: float
    gain: float = 1.0
    pan: float = 0.0
    reverb: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "start_time": self.start_time,
            "duration": self.duration,
            "gain": self.gain,
            "pan": self.pan,
            "reverb": self.reverb,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioSource":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class AudioPlan:
    plan_id: str
    scene_id: str
    sources: List[AudioSource] = field(default_factory=list)
    duration: float = 0.0
    sample_rate: int = 16000
    channels: int = 1
    status: AudioPlanStatus = AudioPlanStatus.DRAFT
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "scene_id": self.scene_id,
            "sources": [s.to_dict() for s in self.sources],
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioPlan":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "status" in filtered and not isinstance(filtered["status"], AudioPlanStatus):
            filtered["status"] = AudioPlanStatus(filtered["status"])
        filtered["sources"] = [AudioSource.from_dict(s) for s in filtered.get("sources", [])]
        return cls(**filtered)

    def add_source(self, source: AudioSource) -> None:
        self.sources.append(source)
        self.duration = max(self.duration, source.start_time + source.duration)


class SoundDirector:
    """High-level scene-to-audio-plan generator."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.plans: Dict[str, AudioPlan] = {}

    def generate_plan(self, scene: DialogueScene, world: Optional[AudioWorld] = None, plan_id: Optional[str] = None) -> AudioPlan:
        plan = AudioPlan(
            plan_id=plan_id or f"plan_{int(time.time())}",
            scene_id=scene.scene_id,
            sample_rate=self.sample_rate,
            channels=self.channels,
        )
        # Convert dialogue turns to audio sources.
        for turn in scene.turns:
            source = AudioSource(
                source_id=turn.turn_id,
                source_type="dialogue",
                start_time=turn.start_time,
                duration=turn.duration,
                gain=1.0,
                pan=0.0,
                reverb=0.0,
                metadata={"speaker": turn.speaker_id, "text": turn.text},
            )
            plan.add_source(source)
        # Add ambience source if world is provided.
        if world is not None:
            ambience = AudioSource(
                source_id="ambience",
                source_type="ambience",
                start_time=0.0,
                duration=plan.duration or 1.0,
                gain=0.3,
                metadata={"weather": world.weather.value, "crowd": world.crowd_density.value},
            )
            plan.add_source(ambience)
        self.plans[plan.plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[AudioPlan]:
        return self.plans.get(plan_id)

    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Optional[AudioPlan]:
        plan = self.plans.get(plan_id)
        if plan is None:
            return None
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        return plan