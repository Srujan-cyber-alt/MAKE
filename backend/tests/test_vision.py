import pytest
import numpy as np


class TestVisionRuntime:
    def test_runtime_report_contains_hardware(self):
        from app.services.vision_runtime import VisionRuntime
        report = VisionRuntime.get_full_runtime_report()
        assert "hardware" in report
        assert "backends" in report
        assert "capabilities" in report
        assert "cpu" in report["hardware"]

    def test_capability_detection_object_detection(self):
        from app.services.vision_runtime import VisionRuntime
        state = VisionRuntime.is_capability_available("object_detection")
        assert isinstance(state, bool)

    def test_capability_detection_segmentation(self):
        from app.services.vision_runtime import VisionRuntime
        state = VisionRuntime.is_capability_available("segmentation")
        assert isinstance(state, bool)

    def test_hardware_detection(self):
        from app.services.vision_runtime import VisionRuntime
        hw = VisionRuntime.detect_hardware()
        assert hw.cpu_count >= 1
        assert hw.memory_gb >= 0


class TestModelRegistry:
    def test_registry_singleton(self):
        from app.services.vision_model_registry import ModelRegistry
        reg = ModelRegistry.get_instance()
        assert reg is not None

    def test_registry_has_default_models(self):
        from app.services.vision_model_registry import ModelRegistry
        reg = ModelRegistry.get_instance()
        summary = reg.get_registry_summary()
        assert len(summary) > 0

    def test_get_by_task(self):
        from app.services.vision_model_registry import ModelRegistry, TaskType
        reg = ModelRegistry.get_instance()
        models = reg.get_by_task(TaskType.OBJECT_DETECTION)
        assert isinstance(models, list)

    def test_update_state(self):
        from app.services.vision_model_registry import ModelRegistry, ModelState
        reg = ModelRegistry.get_instance()
        reg.update_state("yolov8n", ModelState.AVAILABLE)
        model = reg.get("yolov8n")
        assert model.state == ModelState.AVAILABLE


class TestObjectDetection:
    def test_detector_initialization(self):
        from app.services.vision_detection import ObjectDetector, DetectionBackend
        det = ObjectDetector(backend=DetectionBackend.NULL)
        assert det.backend == DetectionBackend.NULL

    def test_null_backend_returns_empty(self):
        from app.services.vision_detection import ObjectDetector, DetectionBackend
        det = ObjectDetector(backend=DetectionBackend.NULL)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        results = det.detect(frame, 0, 0.0)
        assert results == []

    def test_opencv_backend_detects_face(self):
        pytest.importorskip("cv2")
        from app.services.vision_detection import ObjectDetector, DetectionBackend
        det = ObjectDetector(backend=DetectionBackend.OPENCV, model_name="face")
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        results = det.detect(frame, 0, 0.0)
        assert isinstance(results, list)


class TestSegmentation:
    def test_segmentation_null_backend(self):
        from app.services.vision_segmentation import SegmentationEngine
        seg = SegmentationEngine(backend="null")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = seg.segment_person(frame, 0)
        assert result.backend == "null"
        assert result.confidence == 0.0
        assert result.error is not None

    def test_segmentation_rembg_if_available(self):
        pytest.importorskip("rembg")
        from app.services.vision_segmentation import SegmentationEngine
        seg = SegmentationEngine(backend="rembg")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = seg.segment_person(frame, 0)
        assert result.backend == "rembg-u2net"
        assert result.confidence > 0.0


class TestTracking:
    def test_tracking_null_backend(self):
        from app.services.vision_tracking import TrackingEngine
        tracker = TrackingEngine(backend="null")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = tracker.track(frame, [], 0)
        assert result.tracks == []
        assert result.backend == "null"

    def test_tracking_opencv_if_available(self):
        pytest.importorskip("cv2")
        from app.services.vision_tracking import TrackingEngine
        tracker = TrackingEngine(backend="opencv")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        detections = [{"object_id": "obj_0_0", "class_name": "person", "confidence": 0.9, "bbox": [10.0, 10.0, 50.0, 50.0]}]
        result = tracker.track(frame, detections, 0)
        assert isinstance(result.tracks, list)


class TestPoseEstimation:
    def test_pose_null_backend(self):
        from app.services.vision_pose import PoseEstimator
        est = PoseEstimator(backend="null")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = est.estimate(frame, 0, 0.0)
        assert result.backend == "null"
        assert len(result.keypoints) == 0

    def test_pose_opencv_if_available(self):
        pytest.importorskip("cv2")
        from app.services.vision_pose import PoseEstimator
        est = PoseEstimator(backend="opencv")
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        result = est.estimate(frame, 0, 0.0)
        assert isinstance(result.keypoints, list)


class TestMotionExtraction:
    def test_motion_null_backend(self):
        from app.services.vision_motion import MotionExtractor
        ext = MotionExtractor(backend="null")
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(2)]
        result = ext.extract(frames, [0, 1], [0.0, 0.033])
        assert result.backend == "null"
        assert result.motion_type == "static"

    def test_motion_opencv_if_available(self):
        pytest.importorskip("cv2")
        from app.services.vision_motion import MotionExtractor
        ext = MotionExtractor(backend="opencv")
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
        for i in range(1, 3):
            frames[i][10:20, 10:20] = 255
        result = ext.extract(frames, [0, 1, 2], [0.0, 0.033, 0.066])
        assert result.backend == "opencv"
        assert isinstance(result.vectors, list)


class TestCameraMotion:
    def test_camera_null_backend(self):
        from app.services.vision_camera import CameraMotionAnalyzer
        analyzer = CameraMotionAnalyzer(backend="null")
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(2)]
        result = analyzer.analyze(frames)
        assert result.backend == "null"
        assert result.motion_type == "static"

    def test_camera_opencv_if_available(self):
        pytest.importorskip("cv2")
        from app.services.vision_camera import CameraMotionAnalyzer
        analyzer = CameraMotionAnalyzer(backend="opencv")
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
        for i in range(1, 3):
            frames[i] = np.roll(frames[i], 5, axis=1)
        result = analyzer.analyze(frames)
        assert result.backend == "opencv"
        assert isinstance(result.trajectory, list)


class TestOpticalFlow:
    def test_flow_null_backend(self):
        from app.services.vision_optical_flow import OpticalFlowEngine
        engine = OpticalFlowEngine(backend="null")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = engine.compute(frame, 0)
        assert result.backend == "null"

    def test_flow_opencv_if_available(self):
        pytest.importorskip("cv2")
        from app.services.vision_optical_flow import OpticalFlowEngine
        engine = OpticalFlowEngine(backend="opencv")
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2[20:40, 20:40] = 255
        r1 = engine.compute(frame1, 0)
        assert r1.backend == "opencv"
        r2 = engine.compute(frame2, 1)
        assert r2.magnitude >= 0.0


class TestDepthEstimation:
    def test_depth_null_backend(self):
        from app.services.vision_depth import DepthEstimator
        est = DepthEstimator(backend="null")
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = est.estimate(frame)
        assert result is None


class TestSceneUnderstanding:
    def test_scene_with_empty_input(self):
        from app.services.vision_scene import SceneUnderstanding
        scenes = SceneUnderstanding.analyze([], None, None, None, 10.0)
        assert len(scenes) == 1
        assert scenes[0].duration == 10.0

    def test_scene_with_detections(self):
        from app.services.vision_scene import SceneUnderstanding
        detections = [{"class_name": "person", "timestamp": 1.0}, {"class_name": "car", "timestamp": 2.0}]
        camera = {"motion_type": "panning"}
        motion = {"intensity": "medium"}
        scenes = SceneUnderstanding.analyze(detections, motion, camera, [0.0, 5.0, 10.0], 10.0)
        assert len(scenes) == 2
        assert "person" in scenes[0].subjects


class TestVisionPipeline:
    def test_pipeline_with_no_frames(self):
        from app.services.vision_pipeline import VisionPipeline
        import asyncio
        result = asyncio.run(VisionPipeline.analyze_asset("test-asset", frames=None))
        assert result.status == "error"
        assert result.error is not None

    def test_pipeline_with_empty_frames(self):
        from app.services.vision_pipeline import VisionPipeline
        import asyncio
        result = asyncio.run(VisionPipeline.analyze_asset("test-asset", frames=[]))
        assert result.status == "error"

    def test_pipeline_with_frames(self):
        from app.services.vision_pipeline import VisionPipeline
        import asyncio
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
        result = asyncio.run(VisionPipeline.analyze_asset("test-asset", frames=frames, frame_indices=[0, 1, 2], timestamps=[0.0, 0.033, 0.066]))
        assert result.status == "completed"
        assert result.progress == 100.0
        assert isinstance(result.detections, list)
        assert isinstance(result.tracks, list)
        assert isinstance(result.segmentations, list)
        assert isinstance(result.poses, list)
        assert isinstance(result.scenes, list)

    def test_cached_result(self):
        from app.services.vision_pipeline import VisionPipeline
        import asyncio
        cached = asyncio.run(VisionPipeline.get_cached_result("nonexistent-asset"))
        assert cached is None
