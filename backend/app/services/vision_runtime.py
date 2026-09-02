"""
Vision Runtime for MAKE AI Video.

Detects available ML/CV backends, hardware acceleration,
and reports accurate capability states.
"""

import platform
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class BackendState(Enum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


@dataclass
class BackendInfo:
    state: BackendState
    name: str
    version: Optional[str] = None
    device: Optional[str] = None
    error: Optional[str] = None
    capabilities: list = field(default_factory=list)


@dataclass
class HardwareInfo:
    cpu: str = "unknown"
    cpu_count: int = 1
    memory_gb: float = 0.0
    gpu_available: bool = False
    gpu_name: Optional[str] = None
    gpu_memory_gb: float = 0.0
    cuda_available: bool = False
    mps_available: bool = False
    onnx_available: bool = False
    opencv_available: bool = False


class VisionRuntime:
    @staticmethod
    def detect_hardware() -> HardwareInfo:
        info = HardwareInfo()
        info.cpu = platform.processor() or platform.machine()
        info.cpu_count = 1
        try:
            import os
            info.cpu_count = os.cpu_count() or 1
        except Exception:
            pass
        info.memory_gb = VisionRuntime._get_memory_gb()
        info.gpu_available = False
        info.gpu_name = None
        info.gpu_memory_gb = 0.0
        info.cuda_available = False
        info.mps_available = False
        info.onnx_available = False
        info.opencv_available = False
        try:
            import torch
            info.cuda_available = torch.cuda.is_available()
            info.mps_available = torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False
            if info.cuda_available:
                info.gpu_available = True
                info.gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                info.gpu_memory_gb = round(props.total_memory / (1024 ** 3), 1)
        except ImportError:
            pass
        try:
            import onnxruntime
            info.onnx_available = True
        except ImportError:
            pass
        try:
            import cv2
            info.opencv_available = True
        except ImportError:
            pass
        return info

    @staticmethod
    def _get_memory_gb() -> float:
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return round(kb / (1024 * 1024), 1)
        except Exception:
            pass
        try:
            import psutil
            return round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except ImportError:
            return 0.0

    @staticmethod
    def detect_torch() -> BackendInfo:
        try:
            import torch
            version = torch.__version__
            device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="PyTorch",
                version=version,
                device=device,
                capabilities=["tensor_inference", "gpu_acceleration", "model_loading"],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="PyTorch", error="torch not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="PyTorch", error=str(e))

    @staticmethod
    def detect_opencv() -> BackendInfo:
        try:
            import cv2
            version = cv2.__version__
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="OpenCV",
                version=version,
                device="cpu",
                capabilities=["image_io", "video_io", "filtering", "feature_detection", "tracking", "optical_flow"],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="OpenCV", error="cv2 not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="OpenCV", error=str(e))

    @staticmethod
    def detect_onnx() -> BackendInfo:
        try:
            import onnxruntime
            version = onnxruntime.__version__
            providers = []
            try:
                available = onnxruntime.get_available_providers()
                if 'CUDAExecutionProvider' in available:
                    providers.append("cuda")
                if 'CoreMLExecutionProvider' in available:
                    providers.append("coreml")
                providers.append("cpu")
            except Exception:
                providers.append("cpu")
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="ONNX Runtime",
                version=version,
                device=", ".join(providers),
                capabilities=["tensor_inference", "model_loading"] + [f"{p}_execution" for p in providers],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="ONNX Runtime", error="onnxruntime not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="ONNX Runtime", error=str(e))

    @staticmethod
    def detect_transformers() -> BackendInfo:
        try:
            import transformers
            version = transformers.__version__
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="HuggingFace Transformers",
                version=version,
                capabilities=["model_loading", "pipeline_inference"],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="HuggingFace Transformers", error="transformers not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="HuggingFace Transformers", error=str(e))

    @staticmethod
    def detect_rembg() -> BackendInfo:
        try:
            import rembg
            version = getattr(rembg, '__version__', 'unknown')
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="rembg",
                version=version,
                capabilities=["background_removal", "matting"],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="rembg", error="rembg not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="rembg", error=str(e))

    @staticmethod
    def detect_numpy() -> BackendInfo:
        try:
            import numpy
            version = numpy.__version__
            return BackendInfo(
                state=BackendState.AVAILABLE,
                name="NumPy",
                version=version,
                capabilities=["array_operations", "numerical_computing"],
            )
        except ImportError:
            return BackendInfo(state=BackendState.NOT_INSTALLED, name="NumPy", error="numpy not installed")
        except Exception as e:
            return BackendInfo(state=BackendState.ERROR, name="NumPy", error=str(e))

    @staticmethod
    def get_full_runtime_report() -> Dict[str, Any]:
        hardware = VisionRuntime.detect_hardware()
        backends = {
            "torch": VisionRuntime.detect_torch(),
            "opencv": VisionRuntime.detect_opencv(),
            "onnx": VisionRuntime.detect_onnx(),
            "transformers": VisionRuntime.detect_transformers(),
            "rembg": VisionRuntime.detect_rembg(),
            "numpy": VisionRuntime.detect_numpy(),
        }
        capabilities = VisionRuntime._compute_capabilities(backends, hardware)
        return {
            "hardware": {
                "cpu": hardware.cpu,
                "cpu_count": hardware.cpu_count,
                "memory_gb": hardware.memory_gb,
                "gpu_available": hardware.gpu_available,
                "gpu_name": hardware.gpu_name,
                "gpu_memory_gb": hardware.gpu_memory_gb,
                "cuda_available": hardware.cuda_available,
                "mps_available": hardware.mps_available,
                "onnx_available": hardware.onnx_available,
                "opencv_available": hardware.opencv_available,
            },
            "backends": {k: {"state": v.state.value, "name": v.name, "version": v.version, "device": v.device, "error": v.error, "capabilities": v.capabilities} for k, v in backends.items()},
            "capabilities": capabilities,
        }

    @staticmethod
    def _compute_capabilities(backends: Dict[str, BackendInfo], hardware: HardwareInfo) -> Dict[str, Any]:
        caps = {
            "object_detection": BackendState.UNAVAILABLE.value,
            "segmentation": BackendState.UNAVAILABLE.value,
            "matting": BackendState.UNAVAILABLE.value,
            "tracking": BackendState.UNAVAILABLE.value,
            "pose_estimation": BackendState.UNAVAILABLE.value,
            "motion_analysis": BackendState.UNAVAILABLE.value,
            "camera_analysis": BackendState.UNAVAILABLE.value,
            "optical_flow": BackendState.UNAVAILABLE.value,
            "depth_estimation": BackendState.UNAVAILABLE.value,
            "face_analysis": BackendState.UNAVAILABLE.value,
            "scene_understanding": BackendState.NOT_INSTALLED.value,
        }
        if backends.get("opencv", BackendInfo(BackendState.NOT_INSTALLED, "")).state == BackendState.AVAILABLE:
            caps["object_detection"] = BackendState.AVAILABLE.value
            caps["tracking"] = BackendState.AVAILABLE.value
            caps["optical_flow"] = BackendState.AVAILABLE.value
            caps["camera_analysis"] = BackendState.AVAILABLE.value
            caps["motion_analysis"] = BackendState.AVAILABLE.value
            caps["scene_understanding"] = BackendState.AVAILABLE.value
        if backends.get("torch", BackendInfo(BackendState.NOT_INSTALLED, "")).state == BackendState.AVAILABLE:
            caps["segmentation"] = BackendState.AVAILABLE.value
            caps["pose_estimation"] = BackendState.AVAILABLE.value
            caps["depth_estimation"] = BackendState.AVAILABLE.value
            caps["face_analysis"] = BackendState.AVAILABLE.value
        if backends.get("rembg", BackendInfo(BackendState.NOT_INSTALLED, "")).state == BackendState.AVAILABLE:
            caps["matting"] = BackendState.AVAILABLE.value
            caps["segmentation"] = BackendState.AVAILABLE.value
        if backends.get("onnx", BackendInfo(BackendState.NOT_INSTALLED, "")).state == BackendState.AVAILABLE:
            caps["object_detection"] = BackendState.AVAILABLE.value
            caps["segmentation"] = BackendState.AVAILABLE.value
            caps["pose_estimation"] = BackendState.AVAILABLE.value
        return caps

    @staticmethod
    def is_capability_available(capability: str) -> bool:
        report = VisionRuntime.get_full_runtime_report()
        state = report["capabilities"].get(capability, BackendState.UNAVAILABLE.value)
        return state == BackendState.AVAILABLE.value
