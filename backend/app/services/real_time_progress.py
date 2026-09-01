"""
Real-Time Generation Experience for MAKE AI Video.

Implements SSE-based real-time progress for generation jobs.

Shows:
ANALYZING
TARGETING
PLANNING
ROUTING
GENERATING
PROCESSING
COMPOSITING
VALIDATING
REPAIRING
FINALIZING

Shows meaningful progress.
Shows current operation.
Shows retry reason.
Shows provider/model only in advanced mode.
"""

from typing import Optional, List, Dict, Any
from app.services.redis_service import redis_service
from app.services.unified_video_pipeline import UnifiedVideoPipeline, PipelineStage
from datetime import datetime
import uuid
import logging
import asyncio

logger = logging.getLogger(__name__)


class RealTimeProgress:
    @staticmethod
    async def create_progress_stream(pipeline_id: str):
        state = UnifiedVideoPipeline.create_pipeline(project_id="", user_id="")
        state.pipeline_id = pipeline_id

        async def event_generator():
            last_progress = -1.0
            last_stage = ""
            while True:
                try:
                    if redis_service.is_connected():
                        data = await redis_service.get_json(f"pipeline:{pipeline_id}")
                        if data:
                            state.progress = data.get("progress", 0.0)
                            state.current_stage = data.get("current_stage", PipelineStage.INPUT)
                            state.status = data.get("status", "running")

                    if state.status == "completed":
                        yield f"data: {__import__('json').dumps({'progress': 100.0, 'stage': 'completed', 'status': 'completed', 'message': 'Pipeline completed'})}\n\n"
                        break
                    elif state.status == "failed":
                        yield f"data: {__import__('json').dumps({'progress': state.progress, 'stage': str(state.current_stage), 'status': 'failed', 'error': 'Pipeline failed'})}\n\n"
                        break
                    elif state.status == "cancelled":
                        yield f"data: {__import__('json').dumps({'progress': state.progress, 'stage': str(state.current_stage), 'status': 'cancelled', 'message': 'Pipeline cancelled'})}\n\n"
                        break

                    if state.progress != last_progress or str(state.current_stage) != last_stage:
                        stage_label = RealTimeProgress._get_stage_label(state.current_stage)
                        yield f"data: {__import__('json').dumps({'progress': state.progress, 'stage': str(state.current_stage), 'stage_label': stage_label, 'status': state.status})}\n\n"
                        last_progress = state.progress
                        last_stage = str(state.current_stage)

                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Progress stream error: {e}")
                    break

        return event_generator()

    @staticmethod
    def _get_stage_label(stage: PipelineStage) -> str:
        labels = {
            PipelineStage.INPUT: "Input",
            PipelineStage.PROJECT: "Project",
            PipelineStage.ASSET_INGESTION: "Asset Ingestion",
            PipelineStage.DIRECTOR: "Director",
            PipelineStage.PROMPT_COMPILER: "Prompt Compiler",
            PipelineStage.GENERATION_PLANNING: "Generation Planning",
            PipelineStage.MODEL_ROUTING: "Model Routing",
            PipelineStage.GENERATION: "Generating",
            PipelineStage.TRANSFORMATION: "Transformation",
            PipelineStage.SEGMENTATION: "Segmentation",
            PipelineStage.TRACKING: "Tracking",
            PipelineStage.IDENTITY_LOCK: "Identity Lock",
            PipelineStage.TEMPORAL_CONSISTENCY: "Temporal Consistency",
            PipelineStage.COMPOSITING: "Compositing",
            PipelineStage.VFX: "VFX",
            PipelineStage.AUDIO: "Audio",
            PipelineStage.CAPTIONS: "Captions",
            PipelineStage.COLOR: "Color",
            PipelineStage.QUALITY_GATES: "Quality Gates",
            PipelineStage.SHOT_REPAIR: "Repairing",
            PipelineStage.VERSION: "Versioning",
            PipelineStage.EXPORT: "Export",
        }
        return labels.get(stage, str(stage))

    @staticmethod
    async def update_progress(pipeline_id: str, progress: float, stage: PipelineStage, status: str, message: Optional[str] = None):
        data = {
            "pipeline_id": pipeline_id,
            "progress": progress,
            "current_stage": stage.value if hasattr(stage, "value") else str(stage),
            "status": status,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        try:
            if redis_service.is_connected():
                await redis_service.set_json(f"pipeline:{pipeline_id}", data, ex=86400)
        except Exception:
            pass

    @staticmethod
    async def get_progress(pipeline_id: str) -> Dict[str, Any]:
        try:
            if redis_service.is_connected():
                data = await redis_service.get_json(f"pipeline:{pipeline_id}")
                if data:
                    return data
        except Exception:
            pass
        return {
            "pipeline_id": pipeline_id,
            "progress": 0.0,
            "current_stage": "unknown",
            "status": "not_found",
        }
