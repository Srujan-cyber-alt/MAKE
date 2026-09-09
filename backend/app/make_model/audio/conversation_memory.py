"""
Conversation memory: history, turn order, speaker relationships, references.

Stores ordered conversation turns and exposes relationship graphs and
contextual-reference resolution.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ConversationTurn:
    turn_id: str
    speaker_id: str
    text: str
    timestamp: float = field(default_factory=time.time)
    emotion: Optional[Dict[str, float]] = None
    referenced_turn_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "timestamp": self.timestamp,
            "emotion": dict(self.emotion) if self.emotion else None,
            "referenced_turn_ids": list(self.referenced_turn_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


class ConversationMemory:
    """Persistent conversation history with relationships and references."""

    def __init__(self, conversation_id: str = "") -> None:
        self.conversation_id = conversation_id or f"conv_{int(time.time())}"
        self.history: List[ConversationTurn] = []
        self._index: Dict[str, ConversationTurn] = {}
        self.speaker_relationships: Dict[str, Set[str]] = defaultdict(set)
        self.reference_graph: Dict[str, Set[str]] = defaultdict(set)
        self.metadata: Dict[str, Any] = {"created_at": time.time()}

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------
    def add_turn(self, turn: ConversationTurn) -> ConversationTurn:
        self.history.append(turn)
        self._index[turn.turn_id] = turn
        # Update relationships.
        if self.history:
            prev = self.history[-2] if len(self.history) >= 2 else None
            if prev is not None and prev.speaker_id != turn.speaker_id:
                self.speaker_relationships[prev.speaker_id].add(turn.speaker_id)
                self.speaker_relationships[turn.speaker_id].add(prev.speaker_id)
        return turn

    def add_speech(
        self,
        speaker_id: str,
        text: str,
        turn_id: Optional[str] = None,
        emotion: Optional[Dict[str, float]] = None,
        referenced_turn_ids: Optional[List[str]] = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            turn_id=turn_id or f"turn_{len(self.history)}_{int(time.time() * 1000)}",
            speaker_id=speaker_id,
            text=text,
            emotion=emotion,
            referenced_turn_ids=referenced_turn_ids or [],
        )
        self.add_turn(turn)
        for ref in turn.referenced_turn_ids:
            self.reference_graph[turn.turn_id].add(ref)
            self.reference_graph[ref].add(turn.turn_id)
        return turn

    def get_turn(self, turn_id: str) -> Optional[ConversationTurn]:
        return self._index.get(turn_id)

    def remove_turn(self, turn_id: str) -> bool:
        if turn_id not in self._index:
            return False
        turn = self._index.pop(turn_id)
        self.history = [t for t in self.history if t.turn_id != turn_id]
        return True

    def clear(self) -> None:
        self.history.clear()
        self._index.clear()
        self.speaker_relationships.clear()
        self.reference_graph.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def turn_count(self) -> int:
        return len(self.history)

    @property
    def speakers(self) -> List[str]:
        seen: List[str] = []
        for t in self.history:
            if t.speaker_id not in seen:
                seen.append(t.speaker_id)
        return seen

    def get_speaker_turns(self, speaker_id: str) -> List[ConversationTurn]:
        return [t for t in self.history if t.speaker_id == speaker_id]

    def get_recent(self, limit: int = 10) -> List[ConversationTurn]:
        return list(self.history[-limit:])

    def get_relationships(self) -> Dict[str, List[str]]:
        return {k: list(v) for k, v in self.speaker_relationships.items()}

    def resolve_reference(self, turn_id: str, depth: int = 2) -> List[ConversationTurn]:
        """BFS over the reference graph to gather context."""
        if turn_id not in self._index:
            return []
        visited: Set[str] = set()
        queue = [turn_id]
        results: List[ConversationTurn] = []
        while queue and len(visited) < depth * 5:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            turn = self._index.get(current)
            if turn is not None:
                results.append(turn)
            for ref in self.reference_graph.get(current, []):
                if ref not in visited:
                    queue.append(ref)
        return results

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "history": [t.to_dict() for t in self.history],
            "speaker_relationships": {k: list(v) for k, v in self.speaker_relationships.items()},
            "reference_graph": {k: list(v) for k, v in self.reference_graph.items()},
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        mem = cls(conversation_id=data.get("conversation_id", ""))
        mem.metadata = data.get("metadata", {})
        mem.speaker_relationships = defaultdict(set, {k: set(v) for k, v in data.get("speaker_relationships", {}).items()})
        mem.reference_graph = defaultdict(set, {k: set(v) for k, v in data.get("reference_graph", {}).items()})
        for raw in data.get("history", []):
            mem.add_turn(ConversationTurn.from_dict(raw))
        return mem