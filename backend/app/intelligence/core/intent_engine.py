"""Intent Engine — converts natural-language requests into structured Intent objects.

CPU-native pattern matching; no external AI APIs. Local NLP models can be
plugged in later via the ``IntentParser`` protocol without redesigning the
core.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.intelligence.schemas import (
    Intent, IntentResult, IntentCategory, ConstraintSpec, EntityRef,
    EntityType,
)


class IntentParser(ABC):
    """Abstract protocol for intent parsing. Local models may implement this."""

    @abstractmethod
    async def parse(self, request: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        raise NotImplementedError


class RuleBasedIntentParser(IntentParser):
    """Rule-based intent parser using keyword/regex patterns. CPU-native."""

    CATEGORY_PATTERNS: List[tuple[IntentCategory, List[str]]] = [
        (IntentCategory.CREATIVE, ["generate", "create", "make a", "produce a", "new video", "new image", "scene", "cinematic", "shot"]),
        (IntentCategory.EDITING, ["edit", "trim", "cut", "replace", "remove", "delete", "add", "change", "modify", "replace", "background"]),
        (IntentCategory.ANALYSIS, ["analyze", "detect", "identify", "measure", "track", "inspect", "what is", "describe"]),
        (IntentCategory.MEMORY, ["remember", "store", "save", "recall", "who is", "what is", "tell me about"]),
        (IntentCategory.REASONING, ["why", "how", "explain", "plan", "schedule", "decide", "compare"]),
        (IntentCategory.CONVERSATION, ["hello", "hi", "help", "what can you", "who are you"]),
    ]

    ENTITY_PATTERNS: Dict[EntityType, List[str]] = {
        EntityType.PERSON: ["person", "man", "woman", "character", "actor", "user", "individual", "people"],
        EntityType.OBJECT: ["object", "item", "prop", "thing", "product", "car", "ball", "chair", "table"],
        EntityType.LOCATION: ["location", "place", "room", "city", "street", "building", "background", "scene", "environment"],
        EntityType.PROJECT: ["project", "collection", "session", "production"],
        EntityType.SCENE: ["scene", "shot", "frame", "moment"],
        EntityType.ASSET: ["asset", "file", "video", "image", "clip", "resource"],
    }

    CONSTRAINT_PATTERNS: Dict[str, List[str]] = {
        "duration": ["[0-9]+\\s*(seconds|second|secs|sec|s)\\b", "[0-9]+\\s*(minutes|minute|mins|min|min)\\b"],
        "resolution": ["4k", "hd", "1080p", "720p", "4096", "hd", "uhd"],
        "style": ["cinematic", "realistic", "anime", "cartoon", "photorealistic"],
        "camera": ["close up", "wide shot", "medium shot", "over the shoulder", "bird", "dolly", "orbit", "pan"],
    }

    def _detect_category(self, request: str) -> IntentCategory:
        lowered = request.lower()
        scores: Dict[IntentCategory, int] = {}
        for cat, keywords in self.CATEGORY_PATTERNS:
            for kw in keywords:
                if kw in lowered:
                    scores[cat] = scores.get(cat, 0) + 1
        if not scores:
            return IntentCategory.UNKNOWN
        return max(scores, key=scores.get)

    def _detect_entities(self, request: str) -> List[EntityRef]:
        lowered = request.lower()
        entities: List[EntityRef] = []
        seen_names: set[str] = set()
        for etype, keywords in self.ENTITY_PATTERNS.items():
            for kw in keywords:
                idx = lowered.find(kw)
                if idx != -1:
                    name = kw
                    if name not in seen_names:
                        seen_names.add(name)
                        entities.append(EntityRef(type=etype, name=name, attributes={}))
        return entities

    def _detect_constraints(self, request: str) -> List[ConstraintSpec]:
        constraints: List[ConstraintSpec] = []
        for ck, patterns in self.CONSTRAINT_PATTERNS.items():
            for pat in patterns:
                match = re.search(pat, request.lower())
                if match:
                    constraints.append(ConstraintSpec(
                        kind=ck, description=match.group(), value=match.group(), severity="info"
                    ))
        return constraints

    def _detect_required_capabilities(self, category: IntentCategory, request: str) -> List[str]:
        lowered = request.lower()
        caps: List[str] = []
        if category == IntentCategory.CREATIVE:
            caps.append("make_video")
            if "image" in lowered or "photo" in lowered:
                caps.append("make_image")
        elif category == IntentCategory.EDITING:
            if "background" in lowered:
                caps.append("image_editing")
            else:
                caps.append("video_editing")
        elif category == IntentCategory.ANALYSIS:
            caps.append("visual_analysis")
        elif category == IntentCategory.MEMORY:
            caps.append("memory")
        elif category == IntentCategory.REASONING:
            caps.append("reasoning")
        return list(dict.fromkeys(caps))

    async def parse(
        self, request: str, context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        category = self._detect_category(request)
        entities = self._detect_entities(request)
        constraints = self._detect_constraints(request)
        required_caps = self._detect_required_capabilities(category, request)

        clarity = 0.5
        if len(entities) > 0:
            clarity += 0.2
        if len(constraints) > 0:
            clarity += 0.1
        if any(kw in request.lower() for kw in ["create", "make", "generate"]):
            clarity += 0.1
        clarity = min(clarity, 0.95)

        intent = Intent(
            category=category,
            raw_request=request,
            description=self._summarise(request, category),
            priority=int((context or {}).get("priority", 0)),
            constraints=constraints,
            entities=entities,
            parameters=dict(context or {}),
            required_capabilities=required_caps,
            confidence=clarity,
        )

        requires_clarification = clarity < 0.6 and category == IntentCategory.UNKNOWN
        questions: List[str] = []
        if requires_clarification:
            questions.append("Could you clarify what you'd like me to do?")
            questions.append("What type of output are you expecting (video, image, edit)?")

        return IntentResult(
            intent=intent,
            clarity=clarity,
            requires_clarification=requires_clarification,
            clarification_questions=questions,
        )

    def _summarise(self, request: str, category: IntentCategory) -> str:
        return f"{category.value} request: {request[:100]}"


class IntentEngine:
    """Public interface for intent parsing with caching of the active parser."""

    def __init__(self, parser: Optional[IntentParser] = None):
        self._parser: IntentParser = parser or RuleBasedIntentParser()

    @property
    def parser(self) -> IntentParser:
        return self._parser

    @parser.setter
    def parser(self, value: IntentParser) -> None:
        self._parser = value

    async def parse(self, request: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        return await self._parser.parse(request, context)

    async def parse_sync(self, request: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        result = await self.parse(request, context)
        return result.intent
