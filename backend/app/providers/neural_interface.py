"""
Local Neural Provider Interface for MAKE AI Video.

Defines the interface for future local neural generation runtimes (PyTorch,
diffusers, ONNX, ComfyUI, etc.). This module does NOT include any neural
inference code — it only declares the contract that a future GPU runtime
must satisfy to plug into the existing Universal Model Engine.

On machines without GPU/CUDA/PyTorch/diffusers, every neural capability
must report UNAVAILABLE. This module must not fabricate availability.
"""

from typing import Optional, List, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class NeuralRuntimeState(str, Enum):
    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    LOADING = "loading"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    OUT_OF_MEMORY = "out_of_memory"
    CANCELLED = "cancelled"


class ProviderClassification(str, Enum):
    LOCAL_NEURAL = "local_neural"
    LOCAL_PROCEDURAL = "local_procedural"
    DETERMINISTIC_TEST = "deterministic_test"
    CLOUD = "cloud"


class GenerationMode(str, Enum):
    LOCAL_ONLY = "local_only"
    HYBRID = "hybrid"
    CLOUD_ALLOWED = "cloud_allowed"


class NeuralCapability(str, Enum):
    TEXT_TO_IMAGE = "text_to_image"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    VIDEO_EXTENSION = "video_extension"
    MOTION_TRANSFER = "motion_transfer"
    CHARACTER_PERFORMANCE = "character_performance"


@dataclass
class NeuralCapabilityReport:
    capability: str
    state: str
    model_id: Optional[str] = None
    vram_required_gb: Optional[float] = None
    estimated_time_seconds: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class NeuralRuntimeReport:
    classification: str
    state: str
    capabilities: List[NeuralCapabilityReport] = field(default_factory=list)
    gpu_available: bool = False
    vram_gb: Optional[float] = None
    cuda_available: bool = False
    pytorch_available: bool = False
    diffusers_available: bool = False
    onnx_available: bool = False
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": self.classification,
            "state": self.state,
            "gpu_available": self.gpu_available,
            "vram_gb": self.vram_gb,
            "cuda_available": self.cuda_available,
            "pytorch_available": self.pytorch_available,
            "diffusers_available": self.diffusers_available,
            "onnx_available": self.onnx_available,
            "capabilities": [
                {
                    "capability": c.capability,
                    "state": c.state,
                    "model_id": c.model_id,
                    "vram_required_gb": c.vram_required_gb,
                    "reason": c.reason,
                }
                for c in self.capabilities
            ],
            "reason": self.reason,
        }


def detect_hardware() -> Dict[str, Any]:
    """Detect actual GPU/VRAM/CUDA availability. Never fabricates."""
    info = {
        "gpu_available": False,
        "vram_gb": None,
        "cuda_available": False,
        "pytorch_available": False,
        "diffusers_available": False,
        "onnx_available": False,
    }
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            info["gpu_available"] = True
            line = result.stdout.strip().split("\n")[0]
            parts = line.split(",")
            if len(parts) > 1:
                mem_str = parts[1].strip().split()[0]
                try:
                    info["vram_gb"] = float(mem_str) / 1024.0
                except ValueError:
                    pass
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    try:
        import torch
        info["pytorch_available"] = True
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["gpu_available"] = True
            if info["vram_gb"] is None:
                info["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
    except ImportError:
        pass
    try:
        import diffusers
        info["diffusers_available"] = True
    except ImportError:
        pass
    try:
        import onnxruntime
        info["onnx_available"] = True
    except ImportError:
        pass
    return info


def get_neural_runtime_report() -> NeuralRuntimeReport:
    """Return honest neural runtime report. No fabrication."""
    hw = detect_hardware()
    if not hw["gpu_available"] or not hw["pytorch_available"]:
        return NeuralRuntimeReport(
            classification=ProviderClassification.LOCAL_NEURAL.value,
            state=NeuralRuntimeState.UNAVAILABLE.value,
            gpu_available=hw["gpu_available"],
            vram_gb=hw["vram_gb"],
            cuda_available=hw["cuda_available"],
            pytorch_available=hw["pytorch_available"],
            diffusers_available=hw["diffusers_available"],
            onnx_available=hw["onnx_available"],
            capabilities=[
                NeuralCapabilityReport(
                    capability=c.value,
                    state=NeuralRuntimeState.UNAVAILABLE.value,
                    reason="No GPU + PyTorch + diffusers runtime available",
                )
                for c in NeuralCapability
            ],
            reason="Neural generation requires GPU + PyTorch + diffusers (or ONNX Runtime). None available on this machine.",
        )
    cap_reports = []
    for c in NeuralCapability:
        state = NeuralRuntimeState.AVAILABLE.value
        model_id = None
        vram = None
        reason = None
        if c == NeuralCapability.TEXT_TO_IMAGE and not hw["diffusers_available"]:
            state = NeuralRuntimeState.UNAVAILABLE.value
            reason = "diffusers not installed"
        elif c in (
            NeuralCapability.TEXT_TO_VIDEO,
            NeuralCapability.IMAGE_TO_VIDEO,
            NeuralCapability.VIDEO_TO_VIDEO,
            NeuralCapability.VIDEO_EXTENSION,
            NeuralCapability.MOTION_TRANSFER,
            NeuralCapability.CHARACTER_PERFORMANCE,
        ):
            state = NeuralRuntimeState.UNAVAILABLE.value
            reason = "Neural video model not loaded (no model files registered)"
        cap_reports.append(NeuralCapabilityReport(
            capability=c.value, state=state, model_id=model_id, vram_required_gb=vram, reason=reason,
        ))
    return NeuralRuntimeReport(
        classification=ProviderClassification.LOCAL_NEURAL.value,
        state=NeuralRuntimeState.AVAILABLE.value,
        gpu_available=hw["gpu_available"],
        vram_gb=hw["vram_gb"],
        cuda_available=hw["cuda_available"],
        pytorch_available=hw["pytorch_available"],
        diffusers_available=hw["diffusers_available"],
        onnx_available=hw["onnx_available"],
        capabilities=cap_reports,
    )


def get_generation_mode() -> GenerationMode:
    """Return the active generation mode from environment."""
    import os
    mode = os.environ.get("GENERATION_MODE", "LOCAL_ONLY").upper()
    try:
        return GenerationMode(mode)
    except ValueError:
        return GenerationMode.LOCAL_ONLY


def enforce_local_only(provider_classification: str) -> bool:
    """Return True if provider is allowed under current generation mode."""
    mode = get_generation_mode()
    if mode == GenerationMode.LOCAL_ONLY:
        if provider_classification == ProviderClassification.CLOUD.value:
            logger.warning("LOCAL_ONLY: blocked cloud provider execution")
            return False
    return True
