"""Tool Router — clean routing abstraction for MAKE Intelligence Core.

Selects the appropriate tool/subsystem for a given request. The frozen
Video and Image subsystems are accessed ONLY through the abstract
``ToolAdapter`` interface — their files, training, inference, datasets,
checkpoints and tests are never modified.

The router is CPU-native and makes routing decisions based on capability
matching and availability, never by fabricating generation results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.intelligence.schemas import (
    RoutingDecision, ExecutionRequest, ExecutionResult,
    ToolType, Intent, Plan, PlanStep,
)


class ToolAdapter(ABC):
    """Abstract interface that any MAKE subsystem (Video, Image, etc.)
    implements to be routable by the intelligence core.

    This is the ONLY integration point. Subsystems implement this adapter
    without modifying their own architecture.
    """

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError

    def get_capabilities(self) -> List[str]:
        return []


class ToolRouter:
    """Routes requests to the appropriate tool based on intent and capabilities."""

    def __init__(self) -> None:
        self._adapters: Dict[ToolType, ToolAdapter] = {}
        self._adapter_order: List[ToolType] = []
        self._health_cache: Dict[str, Dict[str, Any]] = {}

    def register_adapter(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.tool_type] = adapter
        if adapter.tool_type not in self._adapter_order:
            self._adapter_order.append(adapter.tool_type)
        self._health_cache[adapter.name] = {"status": "unknown", "cached_at": None}

    def unregister_adapter(self, tool_type: ToolType) -> bool:
        if tool_type in self._adapters:
            del self._adapters[tool_type]
            self._adapter_order.remove(tool_type)
            return True
        return False

    def get_adapter(self, tool_type: ToolType) -> Optional[ToolAdapter]:
        return self._adapters.get(tool_type)

    def list_adapters(self) -> List[ToolAdapter]:
        return [self._adapters[t] for t in self._adapter_order if t in self._adapters]

    async def route(
        self,
        intent: Intent,
        plan_step: Optional[PlanStep] = None,
    ) -> RoutingDecision:
        """Select the best tool for a given intent/plan step."""
        required_caps = intent.required_capabilities
        requested_tool: Optional[ToolType] = None

        if plan_step and plan_step.tool != ToolType.OTHER:
            requested_tool = plan_step.tool

        if requested_tool and requested_tool in self._adapters:
            adapter = self._adapters[requested_tool]
            decision = RoutingDecision(
                tool=requested_tool,
                reason=f"Explicitly requested tool type: {requested_tool.value}",
                confidence=0.95,
                selected_model=adapter.name,
            )
            return decision

        # Score each adapter
        best_tool: Optional[ToolType] = None
        best_score: float = 0.0
        best_adapter: Optional[ToolAdapter] = None
        alternatives: List[ToolType] = []

        for tool_type, adapter in self._adapters.items():
            score = self._score_adapter(adapter, required_caps, intent)
            if score > 0:
                alternatives.append(tool_type)
                if score > best_score:
                    best_score = score
                    best_tool = tool_type
                    best_adapter = adapter

        alternatives = [t for t in alternatives if t != best_tool]

        if best_tool is None or best_adapter is None:
            decision = RoutingDecision(
                tool=ToolType.OTHER,
                reason="No registered adapter matches the required capabilities; using default handler",
                confidence=0.2,
                alternative_tools=alternatives,
            )
            return decision

        decision = RoutingDecision(
            tool=best_tool,
            reason=f"Matches required capabilities: {required_caps}",
            confidence=min(best_score, 1.0),
            selected_model=best_adapter.name,
            alternative_tools=alternatives,
        )
        return decision

    def _score_adapter(
        self,
        adapter: ToolAdapter,
        required_caps: List[str],
        intent: Intent,
    ) -> float:
        adapter_caps = set(adapter.get_capabilities())
        if not required_caps:
            return 0.5
        matched = 0
        for cap in required_caps:
            if cap in adapter_caps:
                matched += 1
        if matched == 0:
            return 0.0
        return matched / len(required_caps)

    async def route_request(self, request: ExecutionRequest) -> RoutingDecision:
        """Route a direct execution request (without an intent)."""
        caps = [request.tool.value] if request.tool != ToolType.OTHER else []
        intent = Intent(
            category=intent_category_for_tool(request.tool),
            raw_request=f"{request.action} via {request.tool.value}",
            description=f"Direct execution: {request.action}",
            required_capabilities=caps,
        )
        plan_step = PlanStep(
            action=request.action,
            tool=request.tool,
            inputs=request.inputs,
            parameters=request.parameters,
        )
        return await self.route(intent, plan_step)

    async def execute(
        self,
        request: ExecutionRequest,
        intent: Optional[Intent] = None,
    ) -> ExecutionResult:
        """Route and execute a request through the appropriate adapter."""
        decision = await self.route_request(request) if intent is None else await self.route(intent)
        adapter = self._adapters.get(decision.tool)
        if adapter is None:
            return ExecutionResult(
                tool=decision.tool,
                success=False,
                error=f"No adapter registered for tool type: {decision.tool.value}",
                metadata={"routing_decision": decision.model_dump()},
            )
        result = await adapter.execute(request)
        result.metadata["routing_decision"] = decision.model_dump()
        return result

    async def check_all_health(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for adapter in self.list_adapters():
            try:
                health = await adapter.health_check()
                results[adapter.name] = health
                results[adapter.name]["cached_at"] = datetime.utcnow().isoformat()
            except Exception as e:
                results[adapter.name] = {"status": "error", "error": str(e)}
        self._health_cache = results
        return results


def intent_category_for_tool(tool: ToolType) -> Any:
    from app.intelligence.schemas import IntentCategory
    mapping = {
        ToolType.MAKE_VIDEO: IntentCategory.CREATIVE,
        ToolType.MAKE_IMAGE: IntentCategory.CREATIVE,
        ToolType.IMAGE_EDITING: IntentCategory.EDITING,
        ToolType.VISUAL_ANALYSIS: IntentCategory.ANALYSIS,
        ToolType.SEARCH_KNOWLEDGE: IntentCategory.REASONING,
        ToolType.MEMORY: IntentCategory.MEMORY,
        ToolType.REASONING: IntentCategory.REASONING,
    }
    return mapping.get(tool, IntentCategory.UNKNOWN)
