from typing import Optional, Dict, Any
from app.schemas.phase9 import CameraDefinition, CameraMovement
import logging

logger = logging.getLogger(__name__)


class CameraControlEngine:
    @staticmethod
    def parse_natural_language(prompt: str) -> CameraDefinition:
        prompt_lower = prompt.lower()
        camera = CameraDefinition()

        if "orbit" in prompt_lower:
            camera.movement = CameraMovement.ORBIT.value
        elif "dolly" in prompt_lower:
            camera.movement = CameraMovement.DOLLY.value
        elif "push in" in prompt_lower or "push-in" in prompt_lower:
            camera.movement = CameraMovement.PUSH_IN.value
        elif "pull out" in prompt_lower or "pull-out" in prompt_lower:
            camera.movement = CameraMovement.PULL_OUT.value
        elif "pan" in prompt_lower:
            camera.movement = CameraMovement.PAN.value
        elif "tilt" in prompt_lower:
            camera.movement = CameraMovement.TILT.value
        elif "handheld" in prompt_lower:
            camera.movement = CameraMovement.HANDHELD.value
        elif "crane" in prompt_lower:
            camera.movement = CameraMovement.CRANE.value
        elif "drone" in prompt_lower:
            camera.movement = CameraMovement.DRONE.value
        elif "whip pan" in prompt_lower:
            camera.movement = CameraMovement.WHIP_PAN.value
        elif "rack focus" in prompt_lower or "racking focus" in prompt_lower:
            camera.movement = CameraMovement.RACK_FOCUS.value
        elif "zoom" in prompt_lower:
            camera.movement = CameraMovement.ZOOM.value
        elif "tracking" in prompt_lower:
            camera.movement = CameraMovement.TRACKING.value
        else:
            camera.movement = CameraMovement.STATIC.value

        if "slow" in prompt_lower:
            camera.speed = 0.3
        elif "fast" in prompt_lower:
            camera.speed = 0.8
        else:
            camera.speed = 0.5

        if "around" in prompt_lower or "orbit" in prompt_lower:
            camera.target = {"type": "subject", "mode": "orbit_center"}
            camera.position = {"distance": 3.0, "height": 1.5}

        if "close-up" in prompt_lower or "close up" in prompt_lower:
            camera.position = {"distance": 1.0, "height": 1.5}
        elif "wide" in prompt_lower:
            camera.position = {"distance": 10.0, "height": 3.0}

        lens_keywords = {
            "wide angle": "wide",
            "wide": "wide",
            "telephoto": "telephoto",
            "macro": "macro",
            "fisheye": "fisheye",
            "anamorphic": "anamorphic",
            "normal": "normal",
        }
        for keyword, lens in lens_keywords.items():
            if keyword in prompt_lower:
                camera.lens = lens
                break

        if "shallow depth of field" in prompt_lower or "bokeh" in prompt_lower:
            camera.depth_of_field = "shallow"
        elif "deep focus" in prompt_lower:
            camera.depth_of_field = "deep"

        return camera

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
        return params
