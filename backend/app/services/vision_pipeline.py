"""
Unified Vision Pipeline for MAKE Vision & Performance Engine.

Orchestrates analysis: detection → tracking → segmentation → pose → motion → camera → scene.
"""

from typing import List, Dict, Any, Optional
import uuid
import asyncio
from app.services.vision_runtime import VisionRuntime
from app.services.vision_model_registry import ModelRegistry, ModelState, TaskType
from app.services.vision_detection import ObjectDetector, DetectionBackend
from app.services.vision_segmentation import SegmentationEngine
from app.services.vision_tracking import TrackingEngine
from app.services.vision_pose import PoseEstimator
from app.services.vision_motion import MotionExtractor
from app.services.vision_camera import CameraMotionAnalyzer
from app.services.vision_optical_flow import OpticalFlowEngine
from app.services.vision_depth import DepthEstimator
from app.services.vision_scene import SceneUnderstanding
from app.services.redis_service import redis_service
import json


class VisionPipelineResult:
    def __init__(self, asset_id: str, pipeline_id: str):
        self.asset_id = asset_id
        self.pipeline_id = pipeline_id
        self.status = "pending"
        self.progress: float = 0.0
        self.stage: str = "initializing"
        self.detections: List[Dict] = []
        self.tracks: List[Dict] = []
        self.segmentations: List[Dict] = []
        self.poses: List[Dict] = []
        self.motion: Optional[Dict] = None
        self.camera: Optional[Dict] = None
        self.scenes: List[Dict] = []
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "detections": self.detections,
            "tracks": self.tracks,
            "segmentations": self.segmentations,
            "poses": self.poses,
            "motion": self.motion,
            "camera": self.camera,
            "scenes": self.scenes,
            "error": self.error,
        }


class VisionPipeline:
    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return VisionRuntime.get_full_runtime_report()

    @staticmethod
    def get_model_registry() -> Dict[str, Any]:
        return ModelRegistry.get_instance().get_registry_summary()

    @staticmethod
    async def analyze_asset(asset_id: str, frames: Optional[List[Any]] = None, frame_indices: Optional[List[int]] = None, timestamps: Optional[List[float]] = None, sample_rate: int = 1) -> VisionPipelineResult:
        pipeline_id = str(uuid.uuid4())
        result = VisionPipelineResult(asset_id=asset_id, pipeline_id=pipeline_id)
        result.status = "processing"
        result.stage = "initializing"
        result.progress = 5.0
        try:
            if frames is None or len(frames) == 0:
                result.status = "error"
                result.error = "No frames provided for analysis"
                result.progress = 0.0
                return result
            sampled = frames[::sample_rate]
            sampled_indices = frame_indices[::sample_rate] if frame_indices else list(range(0, len(frames), sample_rate))
            sampled_timestamps = timestamps[::sample_rate] if timestamps else [0.0] * len(sampled)
            result.stage = "detecting_objects"
            result.progress = 15.0
            detector = ObjectDetector(backend=DetectionBackend.OPENCV)
            detections = detector.detect_batch(sampled, sampled_indices, sampled_timestamps)
            result.detections = [
                {
                    "object_id": d.object_id,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                    "bbox": d.bbox,
                    "frame_index": d.frame_index,
                    "timestamp": d.timestamp,
                }
                for batch in detections for d in batch
            ]
            result.progress = 35.0
            result.stage = "tracking_subjects"
            tracker = TrackingEngine()
            tracks = []
            for frame, fi in zip(sampled, sampled_indices):
                frame_dets = [d for batch in detections for d in batch if d.frame_index == fi]
                track_result = tracker.track(frame, [{"object_id": d.object_id, "class_name": d.class_name, "confidence": d.confidence, "bbox": d.bbox} for d in frame_dets], fi)
                for t in track_result.tracks:
                    tracks.append({"track_id": t.track_id, "class_name": t.class_name, "bbox": t.bbox, "frame_index": t.frame_index, "confidence": t.confidence, "state": t.state})
            result.tracks = tracks
            result.progress = 55.0
            result.stage = "segmenting"
            segmenter = SegmentationEngine()
            segmentations = segmenter.segment_batch(sampled, sampled_indices)
            result.segmentations = [
                {"mask_id": s.mask_id, "frame_index": s.frame_index, "confidence": s.confidence, "backend": s.backend, "bbox": s.bbox, "error": s.error}
                for s in segmentations
            ]
            result.progress = 70.0
            result.stage = "estimating_pose"
            pose_est = PoseEstimator()
            poses = pose_est.estimate_batch(sampled, sampled_indices, sampled_timestamps)
            result.poses = [
                {"frame_index": p.frame_index, "timestamp": p.timestamp, "keypoints": [{"name": k.name, "x": k.x, "y": k.y, "confidence": k.confidence} for k in p.keypoints], "confidence": p.confidence, "backend": p.backend}
                for p in poses
            ]
            result.progress = 80.0
            result.stage = "analyzing_motion"
            motion = MotionExtractor().extract(sampled, sampled_indices, sampled_timestamps, tracks)
            result.motion = {"vectors": [{"frame_index": v.frame_index, "magnitude": v.magnitude, "direction": v.direction, "dx": v.dx, "dy": v.dy} for v in motion.vectors], "average_magnitude": motion.average_magnitude, "average_direction": motion.average_direction, "motion_type": motion.motion_type, "intensity": motion.intensity, "backend": motion.backend, "error": motion.error}
            result.progress = 90.0
            result.stage = "analyzing_camera"
            camera = CameraMotionAnalyzer().analyze(sampled)
            result.camera = {"motion_type": camera.motion_type, "confidence": camera.confidence, "intensity": camera.intensity, "trajectory": camera.trajectory, "backend": camera.backend, "error": camera.error}
            result.progress = 95.0
            result.stage = "scene_understanding"
            scenes = SceneUnderstanding.analyze(result.detections, result.motion, result.camera)
            result.scenes = [
                {"scene_index": s.scene_index, "start_time": s.start_time, "end_time": s.end_time, "duration": s.duration, "subjects": s.subjects, "objects": s.objects, "environment": s.environment, "camera_motion": s.camera_motion, "motion_intensity": s.motion_intensity, "lighting": s.lighting, "confidence": s.confidence, "backend": s.backend}
                for s in scenes
            ]
            result.progress = 100.0
            result.stage = "completed"
            result.status = "completed"
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            result.progress = 0.0
            result.stage = "failed"
        cache_key = f"vision:pipeline:{asset_id}"
        try:
            if redis_service.is_connected():
                redis_service.set(cache_key, json.dumps(result.to_dict()), ex=86400)
        except Exception:
            pass
        return result

    @staticmethod
    async def get_cached_result(asset_id: str) -> Optional[Dict[str, Any]]:
        try:
            if redis_service.is_connected():
                data = redis_service.get(f"vision:pipeline:{asset_id}")
                if data:
                    return json.loads(data)
        except Exception:
            pass
        return None
