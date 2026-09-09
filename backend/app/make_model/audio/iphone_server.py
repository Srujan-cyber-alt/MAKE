"""
Lightweight iPhone-controllable audio server.

CPU-first, minimal dependencies, survives disconnect/reconnect.

Supports:
- /status - readiness + model listing
- /jobs - async job creation
- /jobs/{id} - job status, cancellation, progress
- /generate/* - all generation endpoints
- /edit, /enhance, /repair, /spatial, /quality - processing endpoints
- /provenance/{id} - artifact provenance
- /samples - sample listing
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib

from app.make_model.audio.generation import AudioGenerationPipeline
from app.make_model.audio.config_loader import get_default_config
from app.make_model.audio.provenance import AudioProvenanceTracker
from app.make_model.audio.quality import AudioQualityEvaluator
from app.make_model.audio.audio_forensics import AudioForensics


class AudioJob:
    def __init__(self, job_type: str, params: Dict[str, Any]) -> None:
        self.job_id = str(uuid.uuid4())
        self.job_type = job_type
        self.params = params
        self.status: str = "pending"
        self.progress: float = 0.0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.checkpoint_path: Optional[str] = None
        self._cancelled: bool = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True
        self.status = "cancelled"
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "params": self.params,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "checkpoint_path": self.checkpoint_path,
            "cancelled": self._cancelled,
        }


class AudioIPhoneServer:
    MAX_TEXT_LENGTH = 5000
    MAX_DURATION = 120.0
    MIN_DURATION = 0.1
    ALLOWED_DIRS: List[str] = ["/tmp"]
    ALLOWED_ENVIRONMENTS = {"wind", "rain", "forest", "city", "ocean", "night", "interior"}
    ALLOWED_MATERIALS = {"wood", "metal", "glass", "water", "cloth", "stone", "concrete", "soil"}
    VALID_JOB_ID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    def __init__(self, config_path: Optional[str] = None, storage_dir: Optional[str] = None) -> None:
        self.config = get_default_config("tiny")
        self.pipeline: Optional[AudioGenerationPipeline] = None
        self.provenance = AudioProvenanceTracker("/tmp/audio_provenance_iphone.json")
        self.quality = AudioQualityEvaluator()
        self._jobs: Dict[str, AudioJob] = {}
        self._storage_dir = storage_dir or "/tmp/make_audio_storage"
        Path(self._storage_dir).mkdir(parents=True, exist_ok=True)
        self._jobs_path = os.path.join(self._storage_dir, "jobs.json")
        self._load_jobs()

    def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        import uvicorn
        app = self._create_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

    def _create_app(self):
        from fastapi import FastAPI, HTTPException
        app = FastAPI(title="MAKE Audio iPhone Server")

        @app.get("/status")
        async def status():
            models = self.pipeline.list_models() if self.pipeline else []
            return {
                "status": "ready" if self.pipeline else "initializing",
                "models": models,
                "active_jobs": len([j for j in self._jobs.values() if j.status == "running"]),
                "total_jobs": len(self._jobs),
                "storage_dir": self._storage_dir,
            }

        @app.post("/jobs")
        async def create_job(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob(request.get("type", "voice"), request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.get("/jobs/{job_id}")
        async def get_job(job_id: str):
            self._validate_job_id(job_id)
            job = self._jobs.get(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            return job.to_dict()

        @app.post("/jobs/{job_id}/cancel")
        async def cancel_job_endpoint(job_id: str):
            self._validate_job_id(job_id)
            job = self._jobs.get(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            job.cancel()
            self._save_jobs()
            return {"job_id": job_id, "status": "cancelled"}

        @app.post("/generate/voice")
        async def generate_voice(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("voice", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/generate/dialogue")
        async def generate_dialogue(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("dialogue", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/generate/music")
        async def generate_music(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("music", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/generate/soundscape")
        async def generate_soundscape(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("soundscape", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/generate/foley")
        async def generate_foley(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("foley", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/edit")
        async def edit_audio(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("edit", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/enhance")
        async def enhance_audio(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("enhance", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/repair")
        async def repair_audio(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("repair", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/spatial")
        async def spatialize_audio(request: Dict[str, Any]):
            self.validate_request(request)
            job = AudioJob("spatial", request)
            self._jobs[job.job_id] = job
            self._save_jobs()
            asyncio.create_task(self._process_job(job))
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress}

        @app.post("/quality")
        async def quality_report(request: Dict[str, Any]):
            self.validate_request(request)
            return await self._do_quality(request)

        @app.get("/samples")
        async def list_samples():
            files = []
            for root, _, fnames in os.walk(self._storage_dir):
                for fn in fnames:
                    if fn.endswith(".wav"):
                        full = os.path.join(root, fn)
                        files.append({"path": full, "size": os.path.getsize(full)})
            return files

        @app.get("/provenance/{artifact_id}")
        async def get_provenance(artifact_id: str):
            record = self.provenance.get_record(artifact_id)
            if not record:
                raise HTTPException(status_code=404, detail="Provenance record not found")
            return record.__dict__

        return app

    async def _process_job(self, job: AudioJob) -> None:
        try:
            job.status = "running"
            job.started_at = time.time()
            self._save_jobs()
            if self.pipeline is None:
                self.pipeline = AudioGenerationPipeline()
                await self.pipeline.initialize()
            job.progress = 0.1
            self._save_jobs()
            result = await self._execute_job(job)
            job.progress = 1.0
            job.status = "completed"
            job.result = result
            job.completed_at = time.time()
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.progress = 0.0
        finally:
            job.updated_at = time.time()
            self._save_jobs()

    async def _execute_job(self, job: AudioJob) -> Dict[str, Any]:
        if job.cancelled:
            raise RuntimeError("Job cancelled")
        pipeline = self.pipeline
        if pipeline is None:
            pipeline = AudioGenerationPipeline()
            await pipeline.initialize()
            self.pipeline = pipeline
        jt = job.job_type
        params = job.params
        if jt == "voice":
            result = await pipeline.synthesize_voice(
                params.get("text", ""), params.get("voice_id", "default"),
                params.get("emotion"),
            )
        elif jt == "dialogue":
            result = await pipeline.generate_dialogue(
                params.get("script", []), params.get("voices", {}),
            )
        elif jt == "music":
            result = await pipeline.generate_music(
                params.get("prompt", ""), params.get("duration_seconds", 10.0),
                params.get("genre", "ambient"),
            )
        elif jt == "soundscape":
            model = await pipeline.get_model_async("soundscape")
            if not model:
                raise RuntimeError("Soundscape model not available")
            result = await model.generate_soundscape(
                params.get("environment", "wind"), params.get("duration_seconds", 10.0),
                params.get("parameters", {}),
            )
        elif jt == "foley":
            model = await pipeline.get_model_async("foley")
            if not model:
                raise RuntimeError("Foley model not available")
            result = await model.generate_foley(
                params.get("event_type", "footstep"), params.get("timing", 0.0),
                params.get("metadata", {}),
            )
        elif jt == "edit":
            model = await pipeline.get_model_async("editing")
            if not model:
                raise RuntimeError("Editing model not available")
            result = await model.replace_segment(
                params.get("audio_path", ""), params.get("start", 0.0),
                params.get("end", 1.0), params.get("replacement_text", ""),
            )
        elif jt == "enhance":
            model = await pipeline.get_model_async("enhancement")
            if not model:
                raise RuntimeError("Enhancement model not available")
            result = await model.enhance(params.get("audio_path", ""), params.get("parameters", {}))
        elif jt == "repair":
            model = await pipeline.get_model_async("repair")
            if not model:
                raise RuntimeError("Repair model not available")
            rt = params.get("repair_type", "noise")
            if rt == "dereverb":
                result = await model.dereverberate(params.get("audio_path", ""))
            elif rt == "clipping":
                result = await model.repair_clipping(params.get("audio_path", ""))
            else:
                result = await model.remove_noise(params.get("audio_path", ""), None)
        elif jt == "spatial":
            model = await pipeline.get_model_async("spatial")
            if not model:
                raise RuntimeError("Spatial model not available")
            result = await model.spatialize(
                params.get("audio_path", ""), params.get("position", {"x": 0, "y": 0, "z": 0}),
            )
        else:
            raise ValueError(f"Unknown job type: {jt}")
        return {
            "audio_path": result.audio_path,
            "sample_rate": result.sample_rate,
            "channels": result.channels,
            "duration_seconds": result.duration_seconds,
            "latency_ms": result.latency_ms,
            "provenance": result.provenance,
        }

    def validate_request(self, request: Dict[str, Any]) -> None:
        text = request.get("text", "")
        if text and len(text) > self.MAX_TEXT_LENGTH:
            raise ValueError(f"Text exceeds max length {self.MAX_TEXT_LENGTH}")
        duration = request.get("duration_seconds", 5.0)
        if not (self.MIN_DURATION <= duration <= self.MAX_DURATION):
            raise ValueError(f"Duration must be {self.MIN_DURATION}-{self.MAX_DURATION}s")
        if "environment" in request and request["environment"] not in self.ALLOWED_ENVIRONMENTS:
            raise ValueError(f"Unknown environment: {request['environment']}")
        if "material" in request and request["material"] not in self.ALLOWED_MATERIALS:
            raise ValueError(f"Unknown material: {request['material']}")

    def create_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_request(params)
        job = AudioJob(params.get("type", "voice"), params)
        self._jobs[job.job_id] = job
        self._save_jobs()
        return job.to_dict()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        self._validate_job_id(job_id)
        job = self._jobs.get(job_id)
        if job:
            return job.to_dict()
        return None

    def cancel_job(self, job_id: str) -> bool:
        self._validate_job_id(job_id)
        job = self._jobs.get(job_id)
        if job and job.status in ("pending", "running"):
            job.cancel()
            self._save_jobs()
            return True
        return False

    def _validate_job_id(self, job_id: str) -> None:
        import re
        if not re.match(self.VALID_JOB_ID_PATTERN, job_id):
            raise ValueError(f"Invalid job ID format: {job_id}")

    def _validate_path(self, path: str) -> str:
        resolved = os.path.realpath(path)
        for allowed in self.ALLOWED_DIRS:
            if resolved.startswith(os.path.realpath(allowed)):
                return resolved
        raise ValueError(f"Path not in allowed directories: {path}")

    def _load_audio(self, path: str):
        import scipy.io.wavfile as wavfile
        validated = self._validate_path(path)
        return wavfile.read(validated)

    @property
    def _provenance(self) -> AudioProvenanceTracker:
        return self.provenance

    def _load_jobs(self) -> None:
        if os.path.exists(self._jobs_path):
            try:
                with open(self._jobs_path, "r") as f:
                    data = json.load(f)
                for jid, jdata in data.items():
                    job = AudioJob(jdata.get("job_type", "voice"), jdata.get("params", {}))
                    job.job_id = jid
                    job.status = jdata.get("status", "unknown")
                    job.progress = jdata.get("progress", 0.0)
                    job.result = jdata.get("result")
                    job.error = jdata.get("error")
                    job.created_at = jdata.get("created_at", time.time())
                    job.updated_at = jdata.get("updated_at", time.time())
                    job.started_at = jdata.get("started_at")
                    job.completed_at = jdata.get("completed_at")
                    self._jobs[jid] = job
            except Exception:
                pass

    def _save_jobs(self) -> None:
        data = {jid: job.to_dict() for jid, job in self._jobs.items()}
        tmp_path = self._jobs_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, self._jobs_path)

    async def _do_quality(self, request: Dict[str, Any]) -> Dict[str, Any]:
        report = await self.quality.evaluate(request.get("audio_path", ""))
        gate: str
        if report.passed:
            gate = "PASS"
        elif report.overall_score >= 0.3:
            gate = "REVISE"
        else:
            gate = "FAIL"
        return {
            "decision": gate,
            "snr_db": report.snr_db,
            "clipping_ratio": report.clipping_ratio,
            "silence_ratio": report.silence_ratio,
            "spectral_stability": report.spectral_stability,
            "overall_score": report.overall_score,
            "passed": report.passed,
            "details": report.details,
        }
