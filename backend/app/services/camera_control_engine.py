from typing import Optional, List, Dict, Any
from app.schemas.phase9 import CameraDefinition, CameraMovement
import logging

logger = logging.getLogger(__name__)


class CameraControlEngine:
    MOVEMENT_KEYWORDS = {
        "dolly": "dolly",
        "push in": "push_in",
        "push-in": "push_in",
        "pull out": "pull_out",
        "pull-out": "pull_out",
        "orbit": "orbit",
        "pan": "pan",
        "tilt": "tilt",
        "crane": "crane",
        "tracking": "tracking",
        "handheld": "handheld",
        "steadicam": "steadicam",
        "drone": "drone",
        "fpv": "fpv",
        "zoom": "zoom",
        "rack focus": "rack_focus",
        "racking focus": "rack_focus",
        "whip pan": "whip_pan",
        "parallax": "parallax",
        "static": "static",
        "start wide": "static",
        "finish close-up": "push_in",
    }

    LENS_KEYWORDS = {
        "wide angle": "wide",
        "wide": "wide",
        "telephoto": "telephoto",
        "macro": "macro",
        "fisheye": "fisheye",
        "anamorphic": "anamorphic",
        "normal": "normal",
        "portrait": "portrait",
    }

    @staticmethod
    def parse_natural_language(prompt: str) -> CameraDefinition:
        prompt_lower = prompt.lower()
        camera = CameraDefinition()

        movement = CameraControlEngine._parse_movement(prompt_lower)
        camera.movement = movement

        camera.speed = CameraControlEngine._parse_speed(prompt_lower)
        camera.target = CameraControlEngine._parse_target(prompt_lower)
        camera.position = CameraControlEngine._parse_position(prompt_lower)
        camera.lens = CameraControlEngine._parse_lens(prompt_lower)
        camera.depth_of_field = CameraControlEngine._parse_dof(prompt_lower)
        camera.aperture = CameraControlEngine._parse_aperture(prompt_lower)
        camera.focus_distance = CameraControlEngine._parse_focus_distance(prompt_lower)
        camera.shutter_feel = CameraControlEngine._parse_shutter_feel(prompt_lower)
        camera.motion_blur = CameraControlEngine._parse_motion_blur(prompt_lower)
        camera.height = CameraControlEngine._parse_camera_height(prompt_lower)
        camera.angle = CameraControlEngine._parse_camera_angle(prompt_lower)
        camera.fov = CameraControlEngine._parse_fov(prompt_lower)
        camera.easing = CameraControlEngine._parse_easing(prompt_lower)

        return camera

    @staticmethod
    def _parse_movement(prompt_lower: str) -> str:
        for keyword, movement in CameraControlEngine.MOVEMENT_KEYWORDS.items():
            if keyword in prompt_lower:
                return movement
        return "static"

    @staticmethod
    def _parse_speed(prompt_lower: str) -> float:
        if "slowly" in prompt_lower or "slow" in prompt_lower:
            return 0.3
        if "fast" in prompt_lower or "quick" in prompt_lower:
            return 0.8
        if "cinematic" in prompt_lower:
            return 0.4
        return 0.5

    @staticmethod
    def _parse_target(prompt_lower: str) -> Optional[Dict[str, Any]]:
        if "around him" in prompt_lower or "around her" in prompt_lower or "around subject" in prompt_lower:
            return {"type": "subject", "mode": "orbit_center"}
        if "around" in prompt_lower:
            return {"type": "subject", "mode": "orbit"}
        return None

    @staticmethod
    def _parse_position(prompt_lower: str) -> Optional[Dict[str, Any]]:
        if "close-up" in prompt_lower or "close up" in prompt_lower:
            return {"distance": 1.0, "height": 1.5}
        if "wide" in prompt_lower:
            return {"distance": 10.0, "height": 3.0}
        if "low angle" in prompt_lower:
            return {"distance": 3.0, "height": 0.5}
        if "high angle" in prompt_lower or "bird's eye" in prompt_lower:
            return {"distance": 5.0, "height": 10.0}
        return {"distance": 3.0, "height": 1.5}

    @staticmethod
    def _parse_lens(prompt_lower: str) -> Optional[str]:
        for keyword, lens in CameraControlEngine.LENS_KEYWORDS.items():
            if keyword in prompt_lower:
                return lens
        return None

    @staticmethod
    def _parse_dof(prompt_lower: str) -> Optional[str]:
        if "shallow depth of field" in prompt_lower or "bokeh" in prompt_lower:
            return "shallow"
        if "deep focus" in prompt_lower:
            return "deep"
        return None

    @staticmethod
    def _parse_aperture(prompt_lower: str) -> Optional[str]:
        if "wide open" in prompt_lower or "shallow" in prompt_lower:
            return "f/1.4"
        if "closed down" in prompt_lower or "deep" in prompt_lower:
            return "f/16"
        return None

    @staticmethod
    def _parse_focus_distance(prompt_lower: str) -> Optional[float]:
        if "focus on" in prompt_lower:
            return 1.5
        return None

    @staticmethod
    def _parse_shutter_feel(prompt_lower: str) -> Optional[str]:
        if "cinematic" in prompt_lower:
            return "180-degree shutter"
        if "staccato" in prompt_lower or "jittery" in prompt_lower:
            return "90-degree shutter"
        return None

    @staticmethod
    def _parse_motion_blur(prompt_lower: str) -> Optional[str]:
        if "motion blur" in prompt_lower:
            return "natural"
        if "no motion blur" in prompt_lower or "sharp" in prompt_lower:
            return "none"
        return None

    @staticmethod
    def _parse_camera_height(prompt_lower: str) -> Optional[float]:
        if "low angle" in prompt_lower:
            return 0.5
        if "high angle" in prompt_lower or "bird's eye" in prompt_lower:
            return 10.0
        if "eye level" in prompt_lower:
            return 1.5
        return None

    @staticmethod
    def _parse_camera_angle(prompt_lower: str) -> Optional[str]:
        if "low angle" in prompt_lower:
            return "low"
        if "high angle" in prompt_lower or "bird's eye" in prompt_lower:
            return "high"
        if "dutch" in prompt_lower or "tilted" in prompt_lower:
            return "dutch"
        if "eye level" in prompt_lower:
            return "eye_level"
        return None

    @staticmethod
    def _parse_fov(prompt_lower: str) -> Optional[float]:
        if "wide" in prompt_lower:
            return 90.0
        if "telephoto" in prompt_lower:
            return 30.0
        if "normal" in prompt_lower:
            return 50.0
        return None

    @staticmethod
    def _parse_easing(prompt_lower: str) -> Optional[str]:
        if "smooth" in prompt_lower:
            return "ease_in_out"
        if "sudden" in prompt_lower:
            return "linear"
        if "bounce" in prompt_lower:
            return "ease_out_bounce"
        if "vertigo" in prompt_lower or "dolly zoom" in prompt_lower:
            return "vertigo"
        if "arc" in prompt_lower:
            return "arc"
        return None

    @staticmethod
    def _parse_camera_body(prompt_lower: str) -> Optional[str]:
        if "anamorphic" in prompt_lower:
            return "anamorphic"
        if "digital" in prompt_lower:
            return "digital"
        if "film" in prompt_lower:
            return "film"
        if "imax" in prompt_lower:
            return "imax"
        return None

    @staticmethod
    def _parse_sensor_look(prompt_lower: str) -> Optional[str]:
        if "cinematic" in prompt_lower:
            return "cinematic"
        if "raw" in prompt_lower:
            return "raw"
        if "flat" in prompt_lower:
            return "flat"
        if "rec709" in prompt_lower:
            return "rec709"
        return None

    @staticmethod
    def _parse_iso_behavior(prompt_lower: str) -> Optional[str]:
        if "grainy" in prompt_lower or "film grain" in prompt_lower:
            return "high_iso"
        if "clean" in prompt_lower or "low noise" in prompt_lower:
            return "low_iso"
        return None

    @staticmethod
    def parse_natural_language(prompt: str) -> CameraDefinition:
        prompt_lower = prompt.lower()
        camera = CameraDefinition()

        movement = CameraControlEngine._parse_movement(prompt_lower)
        camera.movement = movement

        camera.speed = CameraControlEngine._parse_speed(prompt_lower)
        camera.target = CameraControlEngine._parse_target(prompt_lower)
        camera.position = CameraControlEngine._parse_position(prompt_lower)
        camera.lens = CameraControlEngine._parse_lens(prompt_lower)
        camera.depth_of_field = CameraControlEngine._parse_dof(prompt_lower)
        camera.aperture = CameraControlEngine._parse_aperture(prompt_lower)
        camera.focus_distance = CameraControlEngine._parse_focus_distance(prompt_lower)
        camera.shutter_feel = CameraControlEngine._parse_shutter_feel(prompt_lower)
        camera.motion_blur = CameraControlEngine._parse_motion_blur(prompt_lower)
        camera.height = CameraControlEngine._parse_camera_height(prompt_lower)
        camera.angle = CameraControlEngine._parse_camera_angle(prompt_lower)
        camera.fov = CameraControlEngine._parse_fov(prompt_lower)
        camera.easing = CameraControlEngine._parse_easing(prompt_lower)
        camera.camera_body = CameraControlEngine._parse_camera_body(prompt_lower)
        camera.sensor_look = CameraControlEngine._parse_sensor_look(prompt_lower)
        camera.iso_behavior = CameraControlEngine._parse_iso_behavior(prompt_lower)
        camera.rack_focus = CameraControlEngine._parse_rack_focus(prompt_lower)
        camera.vertigo = CameraControlEngine._parse_vertigo(prompt_lower)
        camera.arc = CameraControlEngine._parse_arc(prompt_lower)
        camera.push_in = CameraControlEngine._parse_push_in(prompt_lower)
        camera.pull_out = CameraControlEngine._parse_pull_out(prompt_lower)

        return camera

    @staticmethod
    def _parse_rack_focus(prompt_lower: str) -> Optional[bool]:
        return "rack focus" in prompt_lower or "racking focus" in prompt_lower

    @staticmethod
    def _parse_vertigo(prompt_lower: str) -> Optional[bool]:
        return "vertigo" in prompt_lower or "dolly zoom" in prompt_lower

    @staticmethod
    def _parse_arc(prompt_lower: str) -> Optional[bool]:
        return "arc" in prompt_lower or "curved" in prompt_lower

    @staticmethod
    def _parse_push_in(prompt_lower: str) -> Optional[bool]:
        return "push in" in prompt_lower or "push-in" in prompt_lower

    @staticmethod
    def _parse_pull_out(prompt_lower: str) -> Optional[bool]:
        return "pull out" in prompt_lower or "pull-out" in prompt_lower

    @staticmethod
    def compile_camera_plan(prompt: str, shot_duration: float = 5.0) -> Dict[str, Any]:
        camera = CameraControlEngine.parse_natural_language(prompt)
        plan = {
            "camera_plan_id": str(__import__("uuid").uuid4()),
            "duration_seconds": shot_duration,
            "camera": camera.model_dump() if hasattr(camera, "model_dump") else camera.__dict__,
            "keyframes": CameraControlEngine._generate_keyframes(camera, shot_duration),
            "provider_parameters": CameraControlEngine.to_generation_parameters(camera),
        }
        return plan

    @staticmethod
    def _generate_keyframes(camera: CameraDefinition, duration: float) -> List[Dict[str, Any]]:
        keyframes = []
        num_keyframes = max(2, int(duration / 2))
        for i in range(num_keyframes):
            keyframes.append({
                "time": i * (duration / max(1, num_keyframes - 1)),
                "position": camera.position,
                "target": camera.target,
                "fov": camera.fov,
            })
        return keyframes

    @staticmethod
    def to_generation_parameters(camera: CameraDefinition) -> Dict[str, Any]:
        params = {}
        if camera.movement:
            params["camera_movement"] = camera.movement
        if camera.speed is not None:
            params["camera_speed"] = camera.speed
        if camera.lens:
            params["lens"] = camera.lens
        if camera.depth_of_field:
            params["depth_of_field"] = camera.depth_of_field
        if camera.position:
            params["camera_position"] = camera.position
        if camera.target:
            params["camera_target"] = camera.target
        if camera.fov:
            params["fov"] = camera.fov
        if camera.easing:
            params["easing"] = camera.easing
        if camera.aperture:
            params["aperture"] = camera.aperture
        if camera.focus_distance is not None:
            params["focus_distance"] = camera.focus_distance
        if camera.shutter_feel:
            params["shutter_feel"] = camera.shutter_feel
        if camera.motion_blur:
            params["motion_blur"] = camera.motion_blur
        if camera.height is not None:
            params["camera_height"] = camera.height
        if camera.angle:
            params["camera_angle"] = camera.angle
        return params
