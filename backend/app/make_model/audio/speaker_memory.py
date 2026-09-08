"""
Speaker memory - multi-speaker consistency and identity tracking.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from app.make_model.audio.types import VoiceGenome


class SpeakerMemory:
    def __init__(self) -> None:
        self._speakers: Dict[str, Dict[str, Any]] = {}
        self._interaction_history: List[Dict[str, Any]] = []

    def register_speaker(self, speaker_id: str, voice_genome: VoiceGenome) -> None:
        self._speakers[speaker_id] = {
            "genome": voice_genome.to_dict(),
            "first_seen": time.time(),
            "last_seen": time.time(),
            "turn_count": 0,
            "emotional_history": [],
        }

    def get_speaker(self, speaker_id: str) -> Optional[Dict[str, Any]]:
        return self._speakers.get(speaker_id)

    def update_speaker(self, speaker_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        speaker = self._speakers.get(speaker_id)
        if not speaker:
            return None
        speaker.update(updates)
        speaker["last_seen"] = time.time()
        speaker["turn_count"] += 1
        return speaker

    def record_interaction(self, speaker_id: str, interaction: Dict[str, Any]) -> None:
        self._interaction_history.append({
            "speaker_id": speaker_id,
            "timestamp": time.time(),
            "interaction": interaction,
        })

    def get_speaker_consistency_score(self, speaker_id: str) -> float:
        speaker = self._speakers.get(speaker_id)
        if not speaker:
            return 0.0
        return min(1.0, speaker["turn_count"] / 10.0)

    def list_speakers(self) -> List[str]:
        return list(self._speakers.keys())

    def get_relationships(self) -> Dict[str, List[str]]:
        relationships = {}
        speakers = list(self._speakers.keys())
        for i, s1 in enumerate(speakers):
            for s2 in speakers[i + 1:]:
                interactions = [
                    entry for entry in self._interaction_history
                    if entry["speaker_id"] in (s1, s2)
                ]
                if interactions:
                    relationships.setdefault(s1, []).append(s2)
                    relationships.setdefault(s2, []).append(s1)
        return relationships
