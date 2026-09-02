from typing import Optional, Dict, Any, List
import os
from app.schemas.phase9 import ColorLookAdjustment, LookPreset
from app.services.video_processing import video_processing_service
import logging

logger = logging.getLogger(__name__)


class ColorPipelineEngine:
    @staticmethod
    def match_color(source_clips: List[Dict[str, Any]], reference_clip: Dict[str, Any]) -> List[Dict[str, Any]]:
        adjustments = []
        for clip in source_clips:
            adjustments.append({
                "clip_id": clip.get("clip_id"),
                "reference_clip_id": reference_clip.get("clip_id"),
                "adjustments": {
                    "exposure": 0.0,
                    "contrast": 0.0,
                    "temperature": 0.0,
                    "saturation": 0.0,
                    "gamma": 0.0,
                },
                "status": "architectured",
                "note": "Color matching requires histogram analysis and LUT generation",
            })
        return adjustments

    @staticmethod
    def build_color_look_filter(preset: str, adjustments: Dict[str, float] = None) -> str:
        adjustments = adjustments or {}
        filters = []
        if "brightness" in adjustments:
            filters.append(f"eq=brightness={adjustments['brightness']}")
        if "contrast" in adjustments:
            filters.append(f"eq=contrast={adjustments['contrast']}")
        if "saturation" in adjustments:
            filters.append(f"eq=saturation={adjustments['saturation']}")
        if "gamma" in adjustments:
            filters.append(f"eq=gamma={adjustments['gamma']}")
        if "temperature" in adjustments:
            filters.append(f"colortemperature=temperature={adjustments['temperature']}")
        if "vignette" in adjustments and adjustments["vignette"] > 0:
            filters.append(f"vignette=angle=PI/4")
        if "grain" in adjustments and adjustments["grain"] > 0:
            filters.append(f"noise=alls={adjustments['grain']}:allf=t")
        return ",".join(filters) if filters else "null"


class ColorLookEngine:
    LOOK_PRESETS = {
        LookPreset.CINEMATIC: {"contrast": 1.2, "saturation": 0.9, "temperature": 0.1, "vignette": 0.3},
        LookPreset.COMMERCIAL: {"contrast": 1.1, "saturation": 1.2, "brightness": 0.05},
        LookPreset.FILM: {"contrast": 1.3, "saturation": 0.8, "grain": 0.1},
        LookPreset.DOCUMENTARY: {"contrast": 1.0, "saturation": 0.9, "temperature": 0.0},
        LookPreset.VINTAGE: {"contrast": 0.9, "saturation": 0.7, "temperature": 0.2, "grain": 0.15},
        LookPreset.NEON: {"contrast": 1.4, "saturation": 1.5, "temperature": -0.1},
        LookPreset.DARK: {"brightness": -0.1, "contrast": 1.3, "saturation": 0.8},
        LookPreset.BRIGHT: {"brightness": 0.1, "contrast": 1.1, "saturation": 1.1},
        LookPreset.WARM: {"temperature": 0.3, "saturation": 1.1},
        LookPreset.COOL: {"temperature": -0.3, "saturation": 0.9},
    }

    @staticmethod
    def apply_look(
        source_path: str,
        output_path: str,
        adjustment: ColorLookAdjustment,
    ) -> Dict[str, Any]:
        if not video_processing_service._check_ffmpeg():
            return {"error": "ffmpeg not available"}

        preset_values = {}
        if adjustment.preset:
            preset_values = ColorLookEngine.LOOK_PRESETS.get(LookPreset(adjustment.preset), {})

        exposure = adjustment.exposure if adjustment.exposure is not None else preset_values.get("exposure", 0.0)
        contrast = adjustment.contrast if adjustment.contrast is not None else preset_values.get("contrast", 1.0)
        saturation = adjustment.saturation if adjustment.saturation is not None else preset_values.get("saturation", 1.0)
        temperature = adjustment.temperature if adjustment.temperature is not None else preset_values.get("temperature", 0.0)
        brightness = adjustment.brightness if adjustment.brightness is not None else preset_values.get("brightness", 0.0)

        filters = []
        if brightness != 0.0:
            filters.append(f"eq=brightness={brightness}")
        if contrast != 1.0:
            filters.append(f"eq=contrast={contrast}")
        if saturation != 1.0:
            filters.append(f"eq=saturation={saturation}")
        if adjustment.highlights is not None:
            filters.append(f"eq=gamma={adjustment.highlights}")
        if adjustment.shadows is not None:
            filters.append(f"eq=gamma={1.0 - adjustment.shadows}")
        if adjustment.grain and adjustment.grain > 0:
            filters.append(f"noise=alls={int(adjustment.grain * 20)}")
        if adjustment.vignette and adjustment.vignette > 0:
            filters.append(f"vignette=angle={adjustment.vignette * 3.14}")

        if not filters:
            return {"output_path": source_path, "status": "no_adjustment"}

        filter_str = ",".join(filters)
        try:
            import subprocess
            cmd = ["ffmpeg", "-y", "-i", source_path, "-vf", filter_str, "-c:v", "libx264", "-preset", "ultrafast", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and os.path.exists(output_path):
                return {"output_path": output_path, "status": "completed", "filters_applied": filters}
            return {"error": "ffmpeg failed", "stderr": result.stderr[-300:] if result.stderr else "", "status": "failed"}
        except Exception as e:
            logger.error(f"Color look application failed: {e}")
            return {"error": str(e), "status": "failed"}

    @staticmethod
    def parse_natural_language(prompt: str) -> ColorLookAdjustment:
        prompt_lower = prompt.lower()
        adjustment = ColorLookAdjustment()

        if "cinematic" in prompt_lower:
            adjustment.preset = LookPreset.CINEMATIC.value
        elif "commercial" in prompt_lower:
            adjustment.preset = LookPreset.COMMERCIAL.value
        elif "vintage" in prompt_lower:
            adjustment.preset = LookPreset.VINTAGE.value
        elif "neon" in prompt_lower:
            adjustment.preset = LookPreset.NEON.value
        elif "dark" in prompt_lower:
            adjustment.preset = LookPreset.DARK.value
        elif "bright" in prompt_lower:
            adjustment.preset = LookPreset.BRIGHT.value
        elif "warm" in prompt_lower:
            adjustment.preset = LookPreset.WARM.value
        elif "cool" in prompt_lower:
            adjustment.preset = LookPreset.COOL.value
        elif "film" in prompt_lower:
            adjustment.preset = LookPreset.FILM.value

        if "grain" in prompt_lower:
            adjustment.grain = 0.2
        if "vignette" in prompt_lower:
            adjustment.vignette = 0.3
        if "high contrast" in prompt_lower:
            adjustment.contrast = 1.4
        if "low contrast" in prompt_lower:
            adjustment.contrast = 0.8
        if "saturated" in prompt_lower:
            adjustment.saturation = 1.3
        if "desaturated" in prompt_lower:
            adjustment.saturation = 0.7

        return adjustment
