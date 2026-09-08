"""Tests for the Intent Engine."""

import pytest

from app.intelligence.core.intent_engine import (
    IntentEngine, RuleBasedIntentParser, IntentParser,
)
from app.intelligence.schemas import IntentCategory, EntityType


class TestIntentParsing:
    @pytest.mark.asyncio
    async def test_creative_intent(self):
        engine = IntentEngine()
        result = await engine.parse("create a cinematic video of a person walking in a city at night")
        assert result.intent.category == IntentCategory.CREATIVE

    @pytest.mark.asyncio
    async def test_editing_intent(self):
        engine = IntentEngine()
        result = await engine.parse("trim the video from 0:05 to 0:10")
        assert result.intent.category == IntentCategory.EDITING

    @pytest.mark.asyncio
    async def test_analysis_intent(self):
        engine = IntentEngine()
        result = await engine.parse("analyze the video and detect objects")
        assert result.intent.category == IntentCategory.ANALYSIS

    @pytest.mark.asyncio
    async def test_memory_intent(self):
        engine = IntentEngine()
        result = await engine.parse("remember that the project name is Project X")
        assert result.intent.category == IntentCategory.MEMORY

    @pytest.mark.asyncio
    async def test_unknown_intent(self):
        engine = IntentEngine()
        result = await engine.parse("xyz random gibberish 123")
        assert result.intent.category == IntentCategory.UNKNOWN

    def test_parse_sync(self):
        import asyncio
        engine = IntentEngine()
        intent = asyncio.get_event_loop().run_until_complete(
            engine.parse_sync("create a cinematic video of a person walking in a city at night")
        )
        assert intent.category == IntentCategory.CREATIVE

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

    @pytest.mark.asyncio
    async def test_entity_detection(self):
        engine = IntentEngine()
        result = await engine.parse("A person walks in the city with a car")
        entity_types = {e.type for e in result.intent.entities}
        assert EntityType.PERSON in entity_types

    @pytest.mark.asyncio
    async def test_constraint_extraction(self):
        engine = IntentEngine()
        result = await engine.parse("create a 10 second cinematic video")
        constraint_kinds = {c.kind for c in result.intent.constraints}
        assert "duration" in constraint_kinds

    @pytest.mark.asyncio
    async def test_required_capabilities(self):
        engine = IntentEngine()
        result = await engine.parse("create a cinematic video")
        assert "make_video" in result.intent.required_capabilities

    @pytest.mark.asyncio
    async def test_clarity_score(self):
        engine = IntentEngine()
        result = await engine.parse("create a cinematic video of a person")
        assert 0.0 <= result.clarity <= 1.0
        assert result.clarity > 0.5

    @pytest.mark.asyncio
    async def test_unclear_request_clarification(self):
        engine = IntentEngine()
        result = await engine.parse("hmm")
        assert result.clarity < 0.6

    def test_parser_protocol(self):
        parser = RuleBasedIntentParser()
        assert isinstance(parser, IntentParser)

    @pytest.mark.asyncio
    async def test_custom_parser(self):
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
        result = await engine.parse("test")
        assert result.intent.category == IntentCategory.REASONING

    def test_rule_based_parser(self):
        parser = RuleBasedIntentParser()
        import asyncio
        intent = asyncio.get_event_loop().run_until_complete(parser.parse("create a video of a sunset"))
        assert intent.intent.category == IntentCategory.CREATIVE
