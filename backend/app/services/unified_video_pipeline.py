"""
Unified Video Pipeline for MAKE AI Video.

Canonical pipeline:
  USER INPUT → PROJECT → ASSET INGESTION → DIRECTOR →
  PROMPT COMPILER → GENERATION PLANNER → SMART MODEL ROUTER →
  GENERATION ENGINE → TRANSFORMATION ENGINE → SEGMENTATION →
  TRACKING → IDENTITY LOCK → TEMPORAL CONSISTENCY → COMPOSITING →
  VFX → AUDIO → CAPTIONS → COLOR → QUALITY GATES → SHOT REPAIR IF REQUIRED →
  VERSION → FINAL ASSET → EXPORT
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    INPUT = "input"
    PROJECT = "project"
    ASSET_INGESTION = "asset_ingestion"
    DIRECTOR = "director"
    PROMPT_COMPILER = "prompt_compiler"
    GENERATION_PLANNING = "generation_planning"
    MODEL_ROUTING = "model_routing"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    SEGMENTATION = "segmentation"
    TRACKING = "tracking"
    IDENTITY_LOCK = "identity_lock"
    TEMPORAL_CONSISTENCY = "temporal_consistency"
    COMPOSITING = "compositing"
    VFX = "vfx"
    AUDIO = "audio"
    CAPTIONS = "captions"
    COLOR = "color"
    QUALITY_GATES = "quality_gates"
    SHOT_REPAIR = "shot_repair"
    VERSION = "version"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class PipelineNodeResult:
    stage: PipelineStage
    status: PipelineStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


@dataclass
class UnifiedPipelineState:
    pipeline_id: str
    project_id: str
    user_id: str
    current_stage: PipelineStage = PipelineStage.INPUT
    status: PipelineStatus = PipelineStatus.PENDING
    progress: float = 0.0
    nodes: Dict[str, PipelineNodeResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    cancelled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedVideoPipeline:
    @staticmethod
    def create_pipeline(project_id: str, user_id: str, max_retries: int = 3) -> UnifiedPipelineState:
        pipeline_id = str(uuid.uuid4())
        return UnifiedPipelineState(
            pipeline_id=pipeline_id,
            project_id=project_id,
            user_id=user_id,
            max_retries=max_retries,
        )

    @staticmethod
    async def execute_stage(
        state: UnifiedPipelineState,
        stage: PipelineStage,
        executor,
    ) -> PipelineNodeResult:
        if state.cancelled:
            return PipelineNodeResult(
                stage=stage,
                status=PipelineStatus.CANCELLED,
                error="Pipeline cancelled by user",
            )

        state.current_stage = stage
        state.status = PipelineStatus.RUNNING
        state.updated_at = datetime.utcnow()

        node_id = f"{state.pipeline_id}:{stage.value}"
        started_at = datetime.utcnow()

        try:
            result = await executor(state)
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            node_result = PipelineNodeResult(
                stage=stage,
                status=PipelineStatus.COMPLETED if not result.get("error") else PipelineStatus.FAILED,
                output=result,
                error=result.get("error"),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

            state.nodes[node_id] = node_result

            if node_result.status == PipelineStatus.FAILED:
                state.errors.append(f"{stage.value}: {node_result.error}")
                state.status = PipelineStatus.FAILED
            else:
                state.progress = UnifiedVideoPipeline._calculate_progress(stage)

            state.updated_at = datetime.utcnow()
            return node_result

        except Exception as e:
            logger.error(f"Pipeline stage {stage.value} failed: {e}")
            completed_at = datetime.utcnow()
            node_result = PipelineNodeResult(
                stage=stage,
                status=PipelineStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )
            state.nodes[node_id] = node_result
            state.errors.append(f"{stage.value}: {str(e)}")
            state.status = PipelineStatus.FAILED
            state.updated_at = datetime.utcnow()
            return node_result

    @staticmethod
    def _calculate_progress(stage: PipelineStage) -> float:
        stage_order = [
            PipelineStage.INPUT,
            PipelineStage.PROJECT,
            PipelineStage.ASSET_INGESTION,
            PipelineStage.DIRECTOR,
            PipelineStage.PROMPT_COMPILER,
            PipelineStage.GENERATION_PLANNING,
            PipelineStage.MODEL_ROUTING,
            PipelineStage.GENERATION,
            PipelineStage.TRANSFORMATION,
            PipelineStage.SEGMENTATION,
            PipelineStage.TRACKING,
            PipelineStage.IDENTITY_LOCK,
            PipelineStage.TEMPORAL_CONSISTENCY,
            PipelineStage.COMPOSITING,
            PipelineStage.VFX,
            PipelineStage.AUDIO,
            PipelineStage.CAPTIONS,
            PipelineStage.COLOR,
            PipelineStage.QUALITY_GATES,
            PipelineStage.SHOT_REPAIR,
            PipelineStage.VERSION,
            PipelineStage.EXPORT,
            PipelineStage.COMPLETED,
        ]
        try:
            index = stage_order.index(stage)
            return min(100.0, (index / (len(stage_order) - 1)) * 100.0)
        except ValueError:
            return 0.0

    @staticmethod
    async def cancel_pipeline(state: UnifiedPipelineState) -> bool:
        state.cancelled = True
        state.status = PipelineStatus.CANCELLED
        state.updated_at = datetime.utcnow()
        return True

    @staticmethod
    async def retry_stage(state: UnifiedPipelineState, stage: PipelineStage, executor) -> Optional[PipelineNodeResult]:
        if state.retry_count >= state.max_retries:
            state.status = PipelineStatus.FAILED
            state.errors.append("Max retries exceeded")
            return None

        state.retry_count += 1
        state.status = PipelineStatus.RETRYING
        node_id = f"{state.pipeline_id}:{stage.value}:retry_{state.retry_count}"

        if node_id in state.nodes:
            del state.nodes[node_id]

        return await UnifiedVideoPipeline.execute_stage(state, stage, executor)
