"""Reasoning Engine — converts Intents into validated, executable Plans.

Pipeline: Intent → constraints → entities → plan → validation → execution →
verification → artifact.
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.intelligence.schemas import (
    Intent, Plan, PlanStep, PlanStatus, IntentResult,
    ConstraintSpec, EntityRef, ToolType, IntentCategory,
)
from app.intelligence.core.intent_engine import IntentEngine
from app.intelligence.core.world_memory import WorldMemory
from app.intelligence.core.reality_graph import RealityGraph
from app.intelligence.core.consistency_engine import ConsistencyEngine


class ReasoningEngine:
    """Transforms intents into structured, validated plans.

    The engine is CPU-native and modular. The plan-to-execution boundary is
    abstracted through the ``on_plan_validated`` hook so the execution
    dispatcher (jobs) can wire in actual tool execution.
    """

    def __init__(
        self,
        intent_engine: Optional[IntentEngine] = None,
        world_memory: Optional[WorldMemory] = None,
        reality_graph: Optional[RealityGraph] = None,
        consistency_engine: Optional[ConsistencyEngine] = None,
    ):
        self._intent_engine = intent_engine or IntentEngine()
        self._world_memory = world_memory or WorldMemory()
        self._reality_graph = reality_graph or RealityGraph()
        self._consistency = consistency_engine or ConsistencyEngine(
            self._world_memory, self._reality_graph
        )

    @property
    def intent_engine(self) -> IntentEngine:
        return self._intent_engine

    @property
    def consistency_engine(self) -> ConsistencyEngine:
        return self._consistency

    # ---- Main entry: intent → plan ----

    async def reason(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Full pipeline: parse intent → enrich with memory/graph → build plan → validate."""
        intent_result: IntentResult = await self._intent_engine.parse(request, context)
        intent = intent_result.intent

        enriched = await self._enrich_intent(intent)
        plan = self._build_plan(enriched, intent_result, context)
        report = self._consistency.check(plan)

        return {
            "intent": intent,
            "plan": plan,
            "consistency_report": report,
            "clarity": intent_result.clarity,
            "requires_clarification": intent_result.requires_clarification,
        }

    async def _enrich_intent(self, intent: Intent) -> Intent:
        """Enrich intent by looking up known entities in world memory."""
        for entity_ref in intent.entities:
            found = await self._world_memory.find_entities(
                entity_type=entity_ref.type, name=entity_ref.name
            )
            if found:
                entity_ref.attributes["memory_id"] = found[0].id
                entity_ref.attributes.setdefault("known", True)
        return intent

    def _build_plan(
        self,
        intent: Intent,
        intent_result: IntentResult,
        context: Optional[Dict[str, Any]],
    ) -> Plan:
        plan = Plan(
            intent_id=intent.id,
            constraints=intent.constraints,
            rationale=f"Plan generated for {intent.category.value} request: {intent.description}",
        )

        required_caps = intent.required_capabilities
        inputs = context or {}

        # Step 1: planning/validation step
        plan.steps.append(PlanStep(
            action="validate_request",
            tool=ToolType.REASONING,
            description="Validate the user request against constraints and available tools",
            inputs={"request": intent.raw_request, "intent": intent.model_dump()},
            expected_outputs=["validated_intent"],
            parameters={"required_capabilities": required_caps},
        ))

        # Step 2: memory recall (if any entities were recognized)
        if intent.entities:
            plan.steps.append(PlanStep(
                action="recall_memory",
                tool=ToolType.MEMORY,
                description="Recall relevant memory for recognized entities",
                inputs={
                    "entities": [e.model_dump() for e in intent.entities],
                    "request": intent.raw_request,
                },
                expected_outputs=["retrieved_entities"],
                depends_on=[plan.steps[-1].id],
            ))

        # Step 3: creative / visual planning for creative requests
        if intent.category == IntentCategory.CREATIVE and "make_video" in required_caps:
            plan.steps.append(PlanStep(
                action="creative_planning",
                tool=ToolType.REASONING,
                description="Generate creative direction (composition, lighting, mood)",
                inputs={"prompt": intent.raw_request, "constraints": [c.model_dump() for c in intent.constraints]},
                expected_outputs=["creative_decision"],
                depends_on=[s.id for s in plan.steps if s.action in ("validate_request", "recall_memory")],
            ))

            plan.steps.append(PlanStep(
                action="visual_planning",
                tool=ToolType.REASONING,
                description="Break the creative brief into shot/scene plans",
                inputs={"creative_decision": "output_of_creative_planning"},
                expected_outputs=["visual_plan"],
                depends_on=[plan.steps[-1].id],
            ))

        # Step 4: routing decision
        routing_step_depends = [plan.steps[-1].id] if plan.steps else []
        if not plan.steps:
            routing_step_depends = []
        plan.steps.append(PlanStep(
            action="route_request",
            tool=ToolType.OTHER,
            description="Select the appropriate tool/provider for execution",
            inputs={"required_capabilities": required_caps, "intent": intent.model_dump()},
            expected_outputs=["routing_decision"],
            depends_on=routing_step_depends,
        ))

        # Step 5: execution
        target_tool = self._select_target_tool(intent, required_caps)
        plan.steps.append(PlanStep(
            action="execute_tool",
            tool=target_tool,
            description=f"Execute the request via {target_tool.value}",
            inputs={**inputs, "intent": intent.model_dump()},
            expected_outputs=["raw_output"],
            depends_on=[plan.steps[-1].id],
            timeout_seconds=intent.parameters.get("timeout_seconds", 120.0),
        ))

        # Step 6: verification
        plan.steps.append(PlanStep(
            action="verify_output",
            tool=ToolType.OTHER,
            description="Verify the output meets requirements",
            inputs={"expected_outputs": plan.steps[-1].expected_outputs},
            expected_outputs=["verification_result"],
            depends_on=[plan.steps[-1].id],
        ))

        # Step 7: artifact registration
        plan.steps.append(PlanStep(
            action="register_artifact",
            tool=ToolType.OTHER,
            description="Register the final output as a traceable artifact",
            inputs={"job_id": context.get("job_id", "") if context else ""},
            expected_outputs=["artifact_record"],
            depends_on=[plan.steps[-1].id],
        ))

        plan.status = PlanStatus.DRAFT
        plan.updated_at = datetime.utcnow()
        return plan

    def _select_target_tool(self, intent: Intent, required_caps: List[str]) -> ToolType:
        if "make_video" in required_caps:
            return ToolType.MAKE_VIDEO
        if "make_image" in required_caps:
            return ToolType.MAKE_IMAGE
        if "image_editing" in required_caps:
            return ToolType.IMAGE_EDITING
        if "visual_analysis" in required_caps:
            return ToolType.VISUAL_ANALYSIS
        if "memory" in required_caps:
            return ToolType.MEMORY
        if "reasoning" in required_caps:
            return ToolType.REASONING
        return ToolType.OTHER

    def validate_plan(self, plan: Plan) -> bool:
        """Quick validation of plan structure without full consistency check."""
        if not plan.steps:
            return False
        step_ids = {s.id for s in plan.steps}
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    return False
        return True
