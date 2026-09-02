"""
Model Registry for MAKE Vision & Performance Engine.

Tracks available vision models, their states, and metadata.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ModelState(Enum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


class ModelFamily(Enum):
    YOLO = "yolo"
    SAM = "sam"
    SAM2 = "sam2"
    DETR = "detr"
    RAFT = "raft"
    DEEP_SORT = "deepsort"
    BYTE_TRACK = "bytetrack"
    SORT = "sort"
    MEDIAN_FLOW = "median_flow"
    REMOTE = "remote"
    OPENCV = "opencv"
    WHISPER = "whisper"
    CUSTOM = "custom"


class TaskType(Enum):
    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    MATTING = "matting"
    POSE_ESTIMATION = "pose_estimation"
    HAND_LANDMARKS = "hand_landmarks"
    FACE_LANDMARKS = "face_landmarks"
    DEPTH_ESTIMATION = "depth_estimation"
    OPTICAL_FLOW = "optical_flow"
    TRACKING = "tracking"
    SCENE_CLASSIFICATION = "scene_classification"
    BACKGROUND_REMOVAL = "background_removal"


@dataclass
class ModelInfo:
    name: str
    family: ModelFamily
    task: TaskType
    version: str
    backend: str
    device_requirements: List[str] = field(default_factory=list)
    input_requirements: Dict[str, Any] = field(default_factory=dict)
    output_type: str = "unknown"
    speed_class: str = "unknown"
    accuracy_class: str = "unknown"
    memory_mb: Optional[int] = None
    state: ModelState = ModelState.NOT_INSTALLED
    installed_path: Optional[str] = None
    download_size_mb: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    _instance: Optional['ModelRegistry'] = None
    _models: Dict[str, ModelInfo] = {}

    @classmethod
    def get_instance(cls) -> 'ModelRegistry':
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_default_models()
        return cls._instance

    def _register_default_models(self):
        defaults = [
            ModelInfo(
                name="yolov8n",
                family=ModelFamily.YOLO,
                task=TaskType.OBJECT_DETECTION,
                version="8n",
                backend="ultralytics",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "image", "channels": 3},
                output_type="bbox",
                speed_class="fast",
                accuracy_class="medium",
                memory_mb=6,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=6,
            ),
            ModelInfo(
                name="yolov8s",
                family=ModelFamily.YOLO,
                task=TaskType.OBJECT_DETECTION,
                version="8s",
                backend="ultralytics",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "image", "channels": 3},
                output_type="bbox",
                speed_class="medium",
                accuracy_class="good",
                memory_mb=22,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=22,
            ),
            ModelInfo(
                name="sam-vit-h",
                family=ModelFamily.SAM,
                task=TaskType.INSTANCE_SEGMENTATION,
                version="vit-h",
                backend="sam",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "image", "channels": 3},
                output_type="mask",
                speed_class="slow",
                accuracy_class="excellent",
                memory_mb=2560,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=2560,
            ),
            ModelInfo(
                name="sam-vit-b",
                family=ModelFamily.SAM,
                task=TaskType.INSTANCE_SEGMENTATION,
                version="vit-b",
                backend="sam",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "image", "channels": 3},
                output_type="mask",
                speed_class="medium",
                accuracy_class="good",
                memory_mb=375,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=375,
            ),
            ModelInfo(
                name="sam2-hiera-tiny",
                family=ModelFamily.SAM2,
                task=TaskType.INSTANCE_SEGMENTATION,
                version="hiera-tiny",
                backend="sam2",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "video", "channels": 3},
                output_type="mask_sequence",
                speed_class="fast",
                accuracy_class="good",
                memory_mb=120,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=120,
            ),
            ModelInfo(
                name="bytetrack",
                family=ModelFamily.BYTE_TRACK,
                task=TaskType.TRACKING,
                version="default",
                backend="bytetrack",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "detections"},
                output_type="track",
                speed_class="fast",
                accuracy_class="good",
                memory_mb=50,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=50,
            ),
            ModelInfo(
                name="opencv-medianflow",
                family=ModelFamily.MEDIAN_FLOW,
                task=TaskType.TRACKING,
                version="default",
                backend="opencv",
                device_requirements=["cpu"],
                input_requirements={"format": "bbox"},
                output_type="track",
                speed_class="fast",
                accuracy_class="low",
                memory_mb=10,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=0,
            ),
            ModelInfo(
                name="rembg-u2net",
                family=ModelFamily.REMOTE,
                task=TaskType.BACKGROUND_REMOVAL,
                version="default",
                backend="rembg",
                device_requirements=["cpu", "cuda"],
                input_requirements={"format": "image", "channels": 3},
                output_type="mask",
                speed_class="medium",
                accuracy_class="good",
                memory_mb=176,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=176,
            ),
            ModelInfo(
                name="opencv-cascade-face",
                family=ModelFamily.OPENCV,
                task=TaskType.OBJECT_DETECTION,
                version="default",
                backend="opencv",
                device_requirements=["cpu"],
                input_requirements={"format": "image", "channels": 1},
                output_type="bbox",
                speed_class="fast",
                accuracy_class="low",
                memory_mb=5,
                state=ModelState.NOT_INSTALLED,
                download_size_mb=5,
            ),
        ]
        for m in defaults:
            self._models[m.name] = m

    def register(self, model: ModelInfo):
        self._models[model.name] = model

    def get(self, name: str) -> Optional[ModelInfo]:
        return self._models.get(name)

    def get_by_task(self, task: TaskType) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.task == task]

    def get_available(self) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.state == ModelState.AVAILABLE]

    def get_available_by_task(self, task: TaskType) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.task == task and m.state == ModelState.AVAILABLE]

    def update_state(self, name: str, state: ModelState, error: Optional[str] = None, installed_path: Optional[str] = None):
        if name in self._models:
            model = self._models[name]
            model.state = state
            model.error = error
            if installed_path:
                model.installed_path = installed_path

    def get_registry_summary(self) -> Dict[str, Any]:
        return {
            name: {
                "name": m.name,
                "family": m.family.value,
                "task": m.task.value,
                "version": m.version,
                "backend": m.backend,
                "state": m.state.value,
                "speed_class": m.speed_class,
                "accuracy_class": m.accuracy_class,
                "memory_mb": m.memory_mb,
                "download_size_mb": m.download_size_mb,
                "error": m.error,
            }
            for name, m in self._models.items()
        }
