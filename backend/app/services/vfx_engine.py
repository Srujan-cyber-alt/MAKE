from typing import Optional, Dict, Any, List
from app.schemas.transformation import VFXLayer, VFXLayerType, BlendMode
from app.services.video_processing import video_processing_service
from app.services.mask_engine import MaskEngine
from app.services.storage import storage_service
import uuid
import logging

logger = logging.getLogger(__name__)


class VFXEngine:
    @staticmethod
    async def apply_vfx(
        base_video_path: str,
        layers: List[VFXLayer],
        output_path: str,
        mask_frames: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not layers:
            return {"output_path": base_video_path, "layers_applied": 0}

        if video_processing_service._check_ffmpeg():
            try:
                from app.services.vfx_compositor import VFXCompositor
                result_path = VFXCompositor.composite_layers(
                    base_video_path=base_video_path,
                    layers=layers,
                    mask_frames=mask_frames,
                    output_path=output_path,
                )
                return {"output_path": result_path, "layers_applied": len(layers)}
            except Exception as e:
                logger.error(f"VFX compositing failed: {e}")
                return {"error": str(e), "layers_applied": 0}
        return {"error": "ffmpeg not available", "layers_applied": 0}

    @staticmethod
    def create_vfx_layer(
        layer_type: str,
        intensity: float = 1.0,
        opacity: float = 1.0,
        blend_mode: str = "normal",
        duration_seconds: Optional[float] = None,
        frame_range: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> VFXLayer:
        return VFXLayer(
            layer_type=VFXLayerType(layer_type),
            blend_mode=BlendMode(blend_mode),
            opacity=opacity,
            intensity=intensity,
            duration_seconds=duration_seconds,
            frame_range=frame_range,
            parameters=parameters or {},
        )

    @staticmethod
    def parse_vfx_from_prompt(prompt: str) -> List[VFXLayer]:
        vfx_keywords = {
            "fire": "fire", "flame": "fire", "smoke": "smoke", "rain": "rain",
            "snow": "snow", "fog": "fog", "sparks": "sparks", "lightning": "lightning",
            "glow": "glow", "explosion": "explosion", "energy": "energy",
            "particles": "cinematic_particles", "dust": "cinematic_particles",
        }
        layers = []
        prompt_lower = prompt.lower()
        for keyword, vfx_type in vfx_keywords.items():
            if keyword in prompt_lower:
                layers.append(VFXEngine.create_vfx_layer(
                    layer_type=vfx_type,
                    intensity=1.0,
                    opacity=0.9,
                    parameters={"source": "prompt", "keyword": keyword},
                ))
        return layers
