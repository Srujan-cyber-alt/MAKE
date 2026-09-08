"""
Lightweight iPhone-controllable audio server.

CPU-first, minimal dependencies, survives disconnect/reconnect.
"""

from __future__ import annotations
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.make_model.audio.generation import AudioGenerationPipeline
from app.make_model.audio.config_loader import get_default_config
from app.make_model.audio.provenance import AudioProvenanceTracker
from app.make_model.audio.quality import AudioQualityEvaluator


class AudioJob:
    def __init__(self, job_type: str, params: Dict[str, Any]) -> None:
        self.job_id = str(uuid.uuid4())
        self.job_type = job_type
        self.params = params
        self.status = "pending"
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at: Optional[float] = None


class AudioIPhoneServer:
    def __init__(self, config_path: Optional[str] = None) -> None:
        self.pipeline = AudioGenerationPipeline(config_path)
        self.provenance = AudioProvenanceTracker("/tmp/audio_provenance_iphone.json")
        self.quality = AudioQualityEvaluator()
        self._jobs: Dict[str, AudioJob] = {}

    def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        import asyncio
        import uvicorn
        app = self._create_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

    def _create_app(self):
        from fastapi import FastAPI
        app = FastAPI(title="MAKE Audio iPhone Server")

        @app.get("/status")
        async def status():
            return {
                "status": "ready",
                "models": self.pipeline.list_models(),
                "jobs": len(self._jobs),
            }

        @app.post("/generate/voice")
        async def generate_voice(request: Dict[str, Any]):
            job = AudioJob("voice", request)
            self._jobs[job.job_id] = job
            return {"job_id": job.job_id, "status": job.status}

        @app.get("/jobs/{job_id}")
        async def get_job(job_id: str):
            job = self._jobs.get(job_id)
            if not job:
                return {"error": "Job not found"}
            return {
                "job_id": job.job_id,
                "status": job.status,
                "result": job.result,
                "error": job.error,
            }

        @app.get("/samples")
        async def list_samples():
            return []

        @app.get("/provenance/{artifact_id}")
        async def get_provenance(artifact_id: str):
            record = self.provenance.get_record(artifact_id)
            if not record:
                return {"error": "Not found"}
            return record.__dict__

        return app
