"""
MAKE Audio API routes.

CPU-first, iPhone-controllable audio generation endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import time
import uuid

from app.make_model.audio.generation import AudioGenerationPipeline
from app.make_model.audio.config_loader import get_default_config
from app.make_model.audio.provenance import AudioProvenanceTracker
from app.make_model.audio.quality import AudioQualityEvaluator
from app.core.auth import get_current_user
from app.make_model.audio.architecture import AudioConfig

router = APIRouter()

_pipeline: Optional[AudioGenerationPipeline] = None
_provenance: Optional[AudioProvenanceTracker] = None
_quality: Optional[AudioQualityEvaluator] = None


def get_pipeline() -> AudioGenerationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AudioGenerationPipeline()
    return _pipeline


def _get_provenance_tracker() -> AudioProvenanceTracker:
    global _provenance
    if _provenance is None:
        _provenance = AudioProvenanceTracker()
    return _provenance


def get_quality() -> AudioQualityEvaluator:
    global _quality
    if _quality is None:
        _quality = AudioQualityEvaluator()
    return _quality


class GenerateVoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: str = Field(default="default")
    emotion: Optional[str] = None
    duration_seconds: float = Field(default=5.0, ge=0.1, le=30.0)


class GenerateDialogueRequest(BaseModel):
    script: List[Dict[str, str]]
    voices: Dict[str, str]


class GenerateMusicRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    duration_seconds: float = Field(default=10.0, ge=0.1, le=120.0)
    genre: str = Field(default="ambient")


class GenerateSoundscapeRequest(BaseModel):
    environment: str = Field(..., min_length=1)
    duration_seconds: float = Field(default=10.0, ge=0.1, le=120.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class GenerateFoleyRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    timing: float = Field(ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MixTracksRequest(BaseModel):
    tracks: List[Dict[str, Any]]
    output_format: str = Field(default="wav")


class ApplyEmotionRequest(BaseModel):
    audio_path: str
    emotion: str
    intensity: float = Field(default=1.0, ge=0.0, le=2.0)


class RepairAudioRequest(BaseModel):
    audio_path: str
    repair_type: str = Field(default="noise")


class SpatializeAudioRequest(BaseModel):
    audio_path: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})


class SpatialSceneRequest(BaseModel):
    sources: List[Dict[str, Any]]
    listener: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})


class EditAudioRequest(BaseModel):
    audio_path: str
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)
    replacement_text: str = Field(..., min_length=1, max_length=5000)


class EnhanceAudioRequest(BaseModel):
    audio_path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class QualityRequest(BaseModel):
    audio_path: str


class AudioResponse(BaseModel):
    audio_path: str
    sample_rate: int
    channels: int
    duration_seconds: float
    model_id: str
    model_version: str
    latency_ms: float
    provenance: Dict[str, Any]


class AudioStatusResponse(BaseModel):
    status: str
    available_models: List[str]
    cpu_profile: Dict[str, Any]


@router.get("/status", response_model=AudioStatusResponse)
async def get_status(current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    cpu_optimizer = pipeline._models.get("cpu_optimization")
    if cpu_optimizer:
        profile = cpu_optimizer.get_profile()
    else:
        profile = {"cpu_count": 1, "available_memory_mb": 4096}
    return AudioStatusResponse(
        status="ready",
        available_models=pipeline.list_models(),
        cpu_profile=profile,
    )


@router.post("/generate/voice", response_model=AudioResponse)
async def generate_voice(request: GenerateVoiceRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    start = time.time()
    result = await pipeline.synthesize_voice(request.text, request.voice_id, request.emotion)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/generate/dialogue", response_model=AudioResponse)
async def generate_dialogue(request: GenerateDialogueRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    start = time.time()
    result = await pipeline.generate_dialogue(request.script, request.voices)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/generate/music", response_model=AudioResponse)
async def generate_music(request: GenerateMusicRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    start = time.time()
    result = await pipeline.generate_music(request.prompt, request.duration_seconds, request.genre)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/generate/soundscape", response_model=AudioResponse)
async def generate_soundscape(request: GenerateSoundscapeRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async("soundscape")
    if not model:
        raise HTTPException(status_code=500, detail="Soundscape model not initialized")
    start = time.time()
    result = await model.generate_soundscape(request.environment, request.duration_seconds, request.parameters)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/generate/foley", response_model=AudioResponse)
async def generate_foley(request: GenerateFoleyRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async("foley")
    if not model:
        raise HTTPException(status_code=500, detail="Foley model not initialized")
    start = time.time()
    result = await model.generate_foley(request.event_type, request.timing, request.metadata)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/mix", response_model=AudioResponse)
async def mix_tracks(request: MixTracksRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    start = time.time()
    result = await pipeline.mix_tracks(request.tracks, request.output_format)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/transform/emotion", response_model=AudioResponse)
async def apply_emotion(request: ApplyEmotionRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    start = time.time()
    result = await pipeline.apply_emotion(request.audio_path, request.emotion, request.intensity)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.get("/samples", response_model=List[Dict[str, Any]])
async def list_samples(current_user=Depends(get_current_user)):
    return []


@router.get("/provenance/{artifact_id}", response_model=Dict[str, Any])
async def get_provenance(artifact_id: str, current_user=Depends(get_current_user)):
    tracker = _get_provenance_tracker()
    record = tracker.get_record(artifact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provenance record not found")
    return record.__dict__


_job_store: Dict[str, Dict[str, Any]] = {}


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


@router.post("/jobs", response_model=JobResponse)
async def create_job(request: GenerateVoiceRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    job_id = str(uuid.uuid4())
    start = time.time()
    result = await pipeline.synthesize_voice(request.text, request.voice_id, request.emotion)
    result.latency_ms = (time.time() - start) * 1000
    _job_store[job_id] = {
        "status": "completed",
        "progress": 1.0,
        "result": {
            "audio_path": result.audio_path,
            "sample_rate": result.sample_rate,
            "channels": result.channels,
            "duration_seconds": result.duration_seconds,
            "latency_ms": result.latency_ms,
        },
        "error": None,
        "provenance": result.provenance,
    }
    return JobResponse(
        job_id=job_id,
        status="completed",
        progress=1.0,
        result={
            "audio_path": result.audio_path,
            "sample_rate": result.sample_rate,
            "channels": result.channels,
            "duration_seconds": result.duration_seconds,
            "latency_ms": result.latency_ms,
        },
        provenance=result.provenance,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, current_user=Depends(get_current_user)):
    job = _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job.get("result"),
        error=job.get("error"),
        provenance=job.get("provenance"),
    )


@router.post("/edit", response_model=AudioResponse)
async def edit_audio(request: EditAudioRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async("editing")
    if not model:
        raise HTTPException(status_code=500, detail="Editing model not initialized")
    start = time.time()
    result = await model.replace_segment(request.audio_path, request.start_seconds, request.end_seconds, request.replacement_text)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/enhance", response_model=AudioResponse)
async def enhance_audio(request: EnhanceAudioRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async("enhancement")
    if not model:
        raise HTTPException(status_code=500, detail="Enhancement model not initialized")
    start = time.time()
    result = await model.enhance(request.audio_path, request.parameters)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/repair", response_model=AudioResponse)
async def repair_audio(request: RepairAudioRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async(request.repair_type)
    if not model:
        raise HTTPException(status_code=500, detail=f"Model for repair_type '{request.repair_type}' not initialized")
    start = time.time()
    if request.repair_type == "noise":
        result = await model.remove_noise(request.audio_path)
    elif request.repair_type == "dereverb":
        result = await model.dereverberate(request.audio_path)
    elif request.repair_type == "clipping":
        result = await model.repair_clipping(request.audio_path)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown repair_type: {request.repair_type}")
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/spatial", response_model=AudioResponse)
async def spatialize_audio(request: SpatializeAudioRequest, current_user=Depends(get_current_user)):
    pipeline = get_pipeline()
    model = await pipeline.get_model_async("spatial")
    if not model:
        raise HTTPException(status_code=500, detail="Spatial model not initialized")
    start = time.time()
    result = await model.spatialize(request.audio_path, request.position)
    result.latency_ms = (time.time() - start) * 1000
    return AudioResponse(
        audio_path=result.audio_path,
        sample_rate=result.sample_rate,
        channels=result.channels,
        duration_seconds=result.duration_seconds,
        model_id=result.model_id,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        provenance=result.provenance,
    )


@router.post("/quality", response_model=Dict[str, Any])
async def quality_report(request: QualityRequest, current_user=Depends(get_current_user)):
    evaluator = get_quality()
    report = await evaluator.evaluate(request.audio_path)
    return {
        "decision": "PASS" if report.passed else "FAIL",
        "snr_db": report.snr_db,
        "clipping_ratio": report.clipping_ratio,
        "silence_ratio": report.silence_ratio,
        "spectral_stability": report.spectral_stability,
        "overall_score": report.overall_score,
        "passed": report.passed,
        "details": report.details,
    }
