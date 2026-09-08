"""Tests for the Tool Router."""

import pytest
from typing import List, Dict, Any

from app.intelligence.core.tool_router import ToolRouter, ToolAdapter, ToolType
from app.intelligence.schemas import ExecutionRequest, ExecutionResult, Intent, IntentCategory, PlanStep


class EchoAdapter(ToolAdapter):
    """Test adapter that echoes execution requests without calling external APIs."""

    def __init__(self, name: str, tool_type: ToolType, capabilities: List[str]):
        self._name = name
        self._tool_type = tool_type
        self._capabilities = capabilities

    @property
    def name(self) -> str:
        return self._name

    @property
    def tool_type(self) -> ToolType:
        return self._tool_type

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "available", "latency_ms": 0.5}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            tool=request.tool,
            success=True,
            artifacts=[{"type": "echo", "input": dict(request.inputs)}],
            metadata={"echo": True},
        )

    def get_capabilities(self) -> List[str]:
        return self._capabilities


class TestToolRouter:
    def test_register_and_list(self):
        router = ToolRouter()
        adapter = EchoAdapter("echo1", ToolType.REASONING, ["reasoning", "memory"])
        router.register_adapter(adapter)
        assert len(router.list_adapters()) == 1

    def test_unregister(self):
        router = ToolRouter()
        adapter = EchoAdapter("echo1", ToolType.MEMORY, ["memory"])
        router.register_adapter(adapter)
        assert router.unregister_adapter(ToolType.MEMORY) is True
        assert len(router.list_adapters()) == 0

    def test_get_adapter(self):
        router = ToolRouter()
        adapter = EchoAdapter("echo1", ToolType.MEMORY, ["memory"])
        router.register_adapter(adapter)
        assert router.get_adapter(ToolType.MEMORY) is adapter

    @pytest.mark.asyncio
    async def test_route_by_tool_type(self):
        router = ToolRouter()
        router.register_adapter(EchoAdapter("echo_video", ToolType.MAKE_VIDEO, ["make_video"]))
        intent = Intent(
            category=IntentCategory.CREATIVE,
            raw_request="create a video",
            required_capabilities=["make_video"],
        )
        plan_step = PlanStep(action="execute_tool", tool=ToolType.MAKE_VIDEO, inputs={})
        decision = await router.route(intent, plan_step)
        assert decision.tool == ToolType.MAKE_VIDEO
        assert decision.confidence > 0

    @pytest.mark.asyncio
    async def test_route_no_matching_adapter(self):
        router = ToolRouter()
        intent = Intent(
            category=IntentCategory.CREATIVE,
            raw_request="create a video",
            required_capabilities=["make_video"],
        )
        decision = await router.route(intent)
        assert decision.tool == ToolType.OTHER
        assert decision.confidence < 0.5

    @pytest.mark.asyncio
    async def test_execute_through_router(self):
        router = ToolRouter()
        router.register_adapter(EchoAdapter("echo", ToolType.REASONING, ["reasoning"]))
        request = ExecutionRequest(tool=ToolType.REASONING, action="test_action", inputs={"q": "hello"})
        result = await router.execute(request)
        assert result.success is True
        assert len(result.artifacts) > 0

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        router = ToolRouter()
        router.register_adapter(EchoAdapter("echo1", ToolType.MEMORY, ["memory"]))
        router.register_adapter(EchoAdapter("echo2", ToolType.REASONING, ["reasoning"]))
        health = await router.check_all_health()
        assert "echo1" in health
        assert "echo2" in health

    @pytest.mark.asyncio
    async def test_route_by_capability(self):
        router = ToolRouter()
        router.register_adapter(EchoAdapter("v1", ToolType.MAKE_VIDEO, ["make_video"]))
        router.register_adapter(EchoAdapter("i1", ToolType.MAKE_IMAGE, ["make_image"]))
        intent = Intent(
            category=IntentCategory.CREATIVE,
            raw_request="create an image",
            required_capabilities=["make_image"],
        )
        decision = await router.route(intent)
        assert decision.tool == ToolType.MAKE_IMAGE

    def test_adapter_protocol(self):
        adapter = EchoAdapter("test", ToolType.MEMORY, ["memory"])
        assert isinstance(adapter, ToolAdapter)
