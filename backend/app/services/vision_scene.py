"""
Scene Understanding for MAKE Vision Engine.

Combines detection, motion, and camera analysis into structured scene intelligence.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SceneSegment:
    scene_index: int
    start_time: float
    end_time: float
    duration: float
    subjects: List[str]
    objects: List[str]
    environment: str
    camera_motion: str
    motion_intensity: str
    lighting: str
    confidence: float = 0.0
    backend: str = "unknown"
    error: Optional[str] = None


class SceneUnderstanding:
    @staticmethod
    def analyze(
        detections: List[Dict],
        motion_analysis: Optional[Dict] = None,
        camera_motion: Optional[Dict] = None,
        scene_changes: Optional[List[float]] = None,
        duration: float = 0.0,
    ) -> List[SceneSegment]:
        if not detections and not scene_changes:
            return [SceneSegment(
                scene_index=0,
                start_time=0.0,
                end_time=duration,
                duration=duration,
                subjects=[],
                objects=[],
                environment="unknown",
                camera_motion=camera_motion.get("motion_type", "static") if camera_motion else "static",
                motion_intensity=motion_analysis.get("intensity", "low") if motion_analysis else "low",
                lighting="unknown",
                confidence=0.0,
                backend="heuristic",
            )]
        segments = []
        boundaries = scene_changes or [0.0, duration]
        if boundaries[-1] < duration:
            boundaries = list(boundaries) + [duration]
        for i in range(len(boundaries) - 1 if len(boundaries) > 1 else 1):
            start = boundaries[i]
            end = boundaries[i + 1] if i + 1 < len(boundaries) else duration
            seg_dets = [d for d in detections if start <= d.get("timestamp", 0) <= end]
            subjects = []
            objects = []
            for det in seg_dets:
                cls = det.get("class_name", "unknown")
                if cls in ("person", "face"):
                    subjects.append(cls)
                else:
                    objects.append(cls)
            camera = camera_motion.get("motion_type", "static") if camera_motion else "static"
            motion_int = motion_analysis.get("intensity", "low") if motion_analysis else "low"
            segments.append(SceneSegment(
                scene_index=i,
                start_time=start,
                end_time=end,
                duration=end - start,
                subjects=list(set(subjects)),
                objects=list(set(objects)),
                environment="unknown",
                camera_motion=camera,
                motion_intensity=motion_int,
                lighting="unknown",
                confidence=0.7 if seg_dets else 0.3,
                backend="heuristic",
            ))
        return segments
