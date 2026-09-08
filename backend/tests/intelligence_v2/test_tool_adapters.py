"""Tests for MAKE Autonomous Agent Core V2 — Tool Adapters."""

import asyncio
import pytest
from app.intelligence.tool_adapters.tool_adapters import (
    ToolRouter,
    ImageToolAdapter,
    VideoToolAdapter,
    ToolRequest,
    ToolCapability,
    ToolStatus,
)


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestImageToolAdapter:
    def test_generate(self):
        adapter = ImageToolAdapter()
        request = ToolRequest(capability=ToolCapability.GENERATE, parameters={"prompt": "test"})
        result = run_async(adapter.execute(request))
        assert result.success is True
        assert result.capability == ToolCapability.GENERATE
        assert result.output["type"] == "image"

    def test_edit(self):
        adapter = ImageToolAdapter()
        request = ToolRequest(capability=ToolCapability.EDIT, parameters={"operation": "blur"})
        result = run_async(adapter.execute(request))
        assert result.success is True
        assert result.output["status"] == "edited"

    def test_inspect(self):
        adapter = ImageToolAdapter()
        request = ToolRequest(capability=ToolCapability.INSPECT, parameters={"asset_id": "123"})
        result = run_async(adapter.execute(request))
        assert result.success is True
        assert result.output["inspection"] == "completed"

    def test_get_capabilities(self):
        adapter = ImageToolAdapter()
        caps = adapter.get_capabilities()
        assert ToolCapability.GENERATE in caps
        assert ToolCapability.EDIT in caps
        assert ToolCapability.INSPECT in caps
        assert ToolCapability.CANCEL in caps


class TestVideoToolAdapter:
    def test_generate(self):
        adapter = VideoToolAdapter()
        request = ToolRequest(capability=ToolCapability.GENERATE, parameters={"prompt": "video"})
        result = run_async(adapter.execute(request))
        assert result.success is True
        assert result.output["type"] == "video"

    def test_get_capabilities(self):
        adapter = VideoToolAdapter()
        caps = adapter.get_capabilities()
        assert len(caps) == 5


class TestToolRouter:
    def test_register_and_execute(self):
        router = ToolRouter()
        router.register_adapter(ImageToolAdapter())
        router.register_adapter(VideoToolAdapter())
        request = ToolRequest(capability=ToolCapability.GENERATE, parameters={"prompt": "test"})
        result = run_async(router.execute("image", request))
        assert result.success is True
        assert result.output["type"] == "image"

    def test_unknown_tool(self):
        router = ToolRouter()
        request = ToolRequest(capability=ToolCapability.GENERATE, parameters={})
        result = run_async(router.execute("unknown", request))
        assert result.success is False
        assert "not found" in result.error

    def test_get_available_tools(self):
        router = ToolRouter()
        router.register_adapter(ImageToolAdapter())
        router.register_adapter(VideoToolAdapter())
        tools = router.get_available_tools()
        assert "image" in tools
        assert "video" in tools
