"""Tests for the Intent Engine."""

import pytest

from app.intelligence.core.intent_engine import (
    IntentEngine, RuleBasedIntentParser, IntentParser,
)
from app.intelligence.schemas import IntentCategory, EntityType


class TestIntentParsing:
    def test_creative_intent(self):
        engine = IntentEngine()
        result = engine.parse_sync("create a cinematic video of a person walking in a city at night")
        assert result.category == IntentCategory.CREATIVE

    def test_editing_intent(self):
        engine = IntentEngine()
        result = engine.parse_sync("trim the video from 0:05 to 0:10")
        assert result.category == IntentCategory.EDITING

    def test_analysis_intent(self):
        engine = IntentEngine()
        result = engine.parse_sync("analyze the video and detect objects")
        assert result.category == IntentCategory.ANALYSIS

    def test_memory_intent(self):
        engine = IntentEngine()
        result = engine.parse_sync("remember that the project name is Project X")
        assert result.category == IntentCategory.MEMORY

    def test_unknown_intent(self):
        engine = IntentEngine()
        result = engine.parse_sync("xyz random gibberish 123")
        assert result.category == IntentCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_async_parse(self):
        engine = IntentEngine()
        result = await engine.parse("create a cinematic video")
        assert result.intent.category == IntentCategory.CREATIVE

    @pytest.mark.asyncio
    async def test_parse_with_context(self):
        engine = IntentEngine()
        result = await engine.parse("make a video", {"priority": 5})
        assert result.intent.priority == 5

    def test_entity_detection(self):
        engine = IntentEngine()
        result = engine.parse_sync("A person walks in the city with a car")
        entity_types = {e.type for e in result.entities}
        assert EntityType.PERSON in entity_types

    def test_constraint_extraction(self):
        engine = IntentEngine()
        result = engine.parse_sync("create a 10 second cinematic video")
        constraint_kinds = {c.kind for c in result.constraints}
        assert "duration" in constraint_kinds

    def test_required_capabilities(self):
        engine = IntentEngine()
        result = engine.parse_sync("create a cinematic video")
        assert "make_video" in result.intent.required_capabilities

    def test_clarity_score(self):
        engine = IntentEngine()
        result = engine.parse_sync("create a cinematic video of a person")
        assert 0.0 <= result.clarity <= 1.0
        assert result.clarity > 0.5

    def test_unclear_request_clarification(self):
        engine = IntentEngine()
        result = engine.parse_sync("do something random xyz")
        assert result.clarity < 0.6

    def test_parser_protocol(self):
        parser = RuleBasedIntentParser()
        assert isinstance(parser, IntentParser)

    def test_custom_parser(self):
        class CustomParser(IntentParser):
            async def parse(self, request, context=None):
                from app.intelligence.schemas import Intent, IntentResult
                intent = Intent(
                    category=IntentCategory.REASONING,
                    raw_request=request,
                    confidence=0.9,
                )
                return IntentResult(intent=intent)
        engine = IntentEngine(parser=CustomParser())
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(engine.parse("test"))
        assert result.intent.category == IntentCategory.REASONING
