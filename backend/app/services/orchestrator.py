import asyncio
import uuid
import httpx
import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.models.models import Job, JobStatus
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse
from app.services.video_processing import video_processing_service
from app.services.asset_registration import asset_registration_service
from app.services.storage import storage_service
from app.services.real_time_progress import RealTimeProgress
from app.core.config import settings

DOWNLOAD_DIR = "/tmp/makeai_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class JobOrchestrator:
    def __init__(self, provider_registry, db_session_factory, storage_service):
        self.provider_registry = provider_registry
        self.db_session_factory = db_session_factory
        self.storage_service = storage_service
        self._running = False
        self._semaphore = asyncio.Semaphore(3)

    async def start(self):
        self._running = True
        while self._running:
            try:
                await self._process_next_job()
                await asyncio.sleep(1)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Orchestrator loop error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False

    async def _process_next_job(self):
        async with self.db_session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Job).where(
                    Job.status == JobStatus.QUEUED,
                    Job.retry_count < Job.max_retries,
                ).order_by(Job.priority.desc(), Job.created_at.asc()).limit(1)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await session.commit()
            await session.refresh(job)

        try:
            async with self._semaphore:
                await self._execute_job(job)
        except Exception as e:
            import traceback
            import logging
            logging.getLogger(__name__).error(f"Orchestrator execute error for job {job.id}: {e}\n{traceback.format_exc()}")
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.retry_count += 1
                    await session.commit()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _execute_job(self, job: Job):
        provider_name = job.provider or settings.default_video_provider
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")

        async with self.db_session_factory() as session:
            job.status = JobStatus.GENERATING
            job.progress = 0.1
            await session.commit()

        await RealTimeProgress.update_progress(
            job.id, 0.1, 
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
            "running",
            "Preparing generation request"
        )

        request = GenerationRequest(
            prompt=job.prompt or "",
            negative_prompt=job.negative_prompt,
            duration_seconds=job.parameters.get("duration_seconds") if job.parameters else None,
            width=job.parameters.get("width") if job.parameters else None,
            height=job.parameters.get("height") if job.parameters else None,
            fps=job.parameters.get("fps") if job.parameters else None,
            input_images=[a.get("url") for a in job.input_assets if a.get("type") == "image"] if job.input_assets else None,
            input_video_url=next((a.get("url") for a in job.input_assets if a.get("type") == "video"), None) if job.input_assets else None,
            reference_images=job.parameters.get("reference_images") if job.parameters else None,
            parameters=job.parameters,
        )

        model_id = job.model or provider.get_supported_models()[0].id if provider.get_supported_models() else None
        if not model_id:
            raise ValueError(f"No model specified and provider {provider_name} has no default model")

        try:
            response = await provider.submit_generation(request, model_id=model_id)
        except Exception as e:
            raise ValueError(f"Provider submission failed: {e}")

        async with self.db_session_factory() as session:
            job = await session.get(Job, job.id)
            if not job:
                return
            job.result = {
                "provider_job_id": response.provider_job_id,
                "status": response.status,
                "model": model_id,
            }
            job.progress = 0.2
            await session.commit()

        await RealTimeProgress.update_progress(
            job.id, 0.2,
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
            "running",
            "Generation submitted, waiting for provider"
        )

        max_polls = 300
        final_status = None
        for i in range(max_polls):
            await asyncio.sleep(5)
            
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job and job.status == JobStatus.CANCELLED:
                    try:
                        await provider.cancel_job(response.provider_job_id)
                    except Exception:
                        pass
                    return

            try:
                status = await provider.check_status(response.provider_job_id)
                final_status = status
                progress = 0.2 + (0.4 * min(i / max_polls, 1.0))
                await RealTimeProgress.update_progress(
                    job.id, progress,
                    __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
                    "running",
                    f"Generating... {int(progress * 100)}%"
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Status check failed: {e}")
                continue

            if status.status in ("completed", "failed", "cancelled"):
                break

        if not final_status or final_status.status not in ("completed",):
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = "Generation did not complete successfully"
                    job.completed_at = datetime.utcnow()
                    await session.commit()
            return

        await RealTimeProgress.update_progress(
            job.id, 0.7,
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
            "running",
            "Downloading result"
        )

        result = await provider.get_result(response.provider_job_id)
        if not result or not result.video_url:
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = "No video URL in result"
                    job.completed_at = datetime.utcnow()
                    await session.commit()
            return

        local_path = os.path.join(DOWNLOAD_DIR, f"{job.id}.mp4")
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(result.video_url, timeout=120.0)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
        except Exception as e:
            async with self.db_session_factory() as session:
                job = await session.get(Job, job.id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error = f"Download failed: {e}"
                    job.completed_at = datetime.utcnow()
                    await session.commit()
            return

        await RealTimeProgress.update_progress(
            job.id, 0.8,
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
            "running",
            "Validating media"
        )

        media_info = None
        if video_processing_service._check_ffmpeg() and video_processing_service._check_ffprobe():
            try:
                media_info = await video_processing_service.inspect_media(local_path)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"FFprobe validation failed: {e}")

        await RealTimeProgress.update_progress(
            job.id, 0.9,
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.GENERATION,
            "running",
            "Registering asset"
        )

        storage_path = None
        try:
            with open(local_path, "rb") as f:
                storage_path, file_size = await self.storage_service.upload_file(
                    f, f"{job.id}.mp4", job.project_id, "video/mp4"
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Upload failed: {e}")

        async with self.db_session_factory() as session:
            job = await session.get(Job, job.id)
            if not job:
                return

            job.status = JobStatus.COMPLETED
            job.output_assets = [{
                "type": "video",
                "url": result.video_url,
                "storage_path": storage_path,
                "thumbnail_url": result.thumbnail_url,
                "duration_seconds": result.duration_seconds,
                "width": result.width,
                "height": result.height,
                "fps": result.fps,
            }]
            job.result = {
                "provider_job_id": result.provider_job_id,
                "video_url": result.video_url,
                "storage_path": storage_path,
                "duration_seconds": result.duration_seconds,
                "width": result.width,
                "height": result.height,
                "fps": result.fps,
                "seed": result.seed,
                "metadata": result.metadata,
                "media_info": media_info.__dict__ if media_info else None,
            }
            job.progress = 1.0
            job.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(job)

            if storage_path and job.project_id:
                try:
                    await asset_registration_service.register_generated_asset(
                        job_id=job.id,
                        project_id=job.project_id,
                        user_id=job.user_id,
                        storage_path=storage_path,
                        video_url=result.video_url,
                        thumbnail_url=result.thumbnail_url,
                        duration_seconds=result.duration_seconds,
                        width=result.width,
                        height=result.height,
                        fps=result.fps,
                        provider=job.provider,
                        model=job.model,
                        prompt=job.prompt,
                        shot_id=job.shot_id,
                        scene_id=job.scene_id,
                        plan_id=job.plan_id,
                        media_info=media_info,
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Asset registration failed: {e}")

        await RealTimeProgress.update_progress(
            job.id, 1.0,
            __import__("app.services.unified_video_pipeline", fromlist=["PipelineStage"]).PipelineStage.COMPLETED,
            "completed",
            "Generation completed"
        )

    async def cancel_job(self, job_id: str) -> bool:
        async with self.db_session_factory() as session:
            job = await session.get(Job, job_id)
            if not job:
                return False
            job.status = JobStatus.CANCELLED
            await session.commit()

        provider = self.provider_registry.get(job.provider) if job.provider else None
        if provider and job.result and job.result.get("provider_job_id"):
            try:
                return await provider.cancel_job(job.result["provider_job_id"])
            except Exception:
                pass
        return True
