from typing import List, Dict, Any, Optional
from app.schemas.transformation import VFXLayer, BlendMode
from app.services.video_processing import video_processing_service
from app.services.mask_engine import MaskEngine
import uuid


class VFXCompositor:
    @staticmethod
    def composite_layers(
        base_video_path: str,
        layers: List[VFXLayer],
        mask_frames: Optional[List[Dict[str, Any]]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        if not layers:
            return base_video_path

        if output_path is None:
            output_path = f"/tmp/vfx_composite_{uuid.uuid4().hex}.mp4"

        filter_parts = [f"[0:v]format=yuva420p[base]"]
        current_label = "base"

        for i, layer in enumerate(layers):
            layer_label = f"layer{i}"
            layer_input = VFXCompositor._generate_vfx_layer(layer, layer_label)
            filter_parts.append(layer_input)

            blend = VFXCompositor._resolve_blend(layer.blend_mode)
            opacity = layer.opacity
            filter_parts.append(
                f"[{current_label}][{layer_label}]blend=all_mode={blend}:all_opacity={opacity}[out{i}]"
            )
            current_label = f"out{i}"

        final_label = current_label
        filter_str = ";".join(filter_parts)
        filter_str = filter_str.replace(f"[{final_label}]", "")

        if mask_frames:
            mask_filter = MaskEngine.apply_mask_to_video(base_video_path, mask_frames, output_path, blend_mode="normal")
            return mask_filter

        safe_filter = VFXCompositor._sanitize_filter(filter_str)
        return video_processing_service.apply_filter(base_video_path, safe_filter, output_path)

    @staticmethod
    def _generate_vfx_layer(layer: VFXLayer, label: str) -> str:
        layer_type = layer.layer_type.value
        intensity = layer.intensity
        params = layer.parameters or {}

        if layer_type == "fire":
            return VFXCompositor._noise_layer(label, "fire", intensity, params, color="red")
        elif layer_type == "smoke":
            return VFXCompositor._noise_layer(label, "smoke", intensity, params, color="gray")
        elif layer_type == "rain":
            return VFXCompositor._particle_layer(label, "rain", intensity, params)
        elif layer_type == "snow":
            return VFXCompositor._particle_layer(label, "snow", intensity, params)
        elif layer_type == "fog":
            return VFXCompositor._noise_layer(label, "fog", intensity, params, color="white")
        elif layer_type == "sparks":
            return VFXCompositor._particle_layer(label, "sparks", intensity, params, color="yellow")
        elif layer_type == "lightning":
            return VFXCompositor._flash_layer(label, intensity)
        elif layer_type == "glow":
            return VFXCompositor._glow_layer(label, intensity)
        elif layer_type == "explosion":
            return VFXCompositor._noise_layer(label, "explosion", intensity, params, color="orange")
        elif layer_type == "energy":
            return VFXCompositor._glow_layer(label, intensity, color="blue")
        elif layer_type == "atmospheric":
            return VFXCompositor._noise_layer(label, "atmospheric", intensity * 0.5, params, color="white")
        elif layer_type == "debris":
            return VFXCompositor._particle_layer(label, "debris", intensity, params)
        elif layer_type == "cinematic_particles":
            return VFXCompositor._particle_layer(label, "cinematic_particles", intensity * 0.3, params)
        else:
            return VFXCompositor._noise_layer(label, layer_type, intensity, params)

    @staticmethod
    def _noise_layer(label: str, noise_type: str, intensity: float, params: Dict[str, Any], color: str = "white") -> str:
        seed = params.get("seed", 42)
        scale = params.get("scale", 100)
        speed = params.get("speed", 1.0)
        return (
            f"color=c={color}:s=1920x1080:d=1,"
            f"noise=alls={seed}:allf=t,"
            f"colorchannelmixer=rr={intensity}:gg={intensity}:bb={intensity}[{label}]"
        )

    @staticmethod
    def _particle_layer(label: str, particle_type: str, intensity: float, params: Dict[str, Any], color: str = "white") -> str:
        count = int(params.get("count", 100) * intensity)
        return (
            f"color=c={color}:s=1920x1080:d=1,"
            f"noise=alls=42:allf=t,"
            f"geq=lum='random(0,{count})':cb=128:cr=128[particles];"
            f"[particles]colorchannelmixer=rr={intensity}:gg={intensity}:bb={intensity}[{label}]"
        )

    @staticmethod
    def _flash_layer(label: str, intensity: float) -> str:
        return (
            f"color=c=white:s=1920x1080:d=1,"
            f"fade=t=in:st=0:d={intensity * 0.5},"
            f"fade=t=out:st={intensity * 0.5}:d={intensity * 0.5}[{label}]"
        )

    @staticmethod
    def _glow_layer(label: str, intensity: float, color: str = "white") -> str:
        return (
            f"color=c={color}:s=1920x1080:d=1,"
            f"boxblur=10:1,"
            f"colorchannelmixer=rr={intensity}:gg={intensity}:bb={intensity}[{label}]"
        )

    @staticmethod
    def _resolve_blend(blend_mode: BlendMode) -> str:
        mapping = {
            BlendMode.NORMAL: "normal",
            BlendMode.OVERLAY: "overlay",
            BlendMode.SCREEN: "screen",
            BlendMode.MULTIPLY: "multiply",
            BlendMode.ADD: "add",
            BlendMode.SOFT_LIGHT: "softlight",
        }
        return mapping.get(blend_mode, "normal")

    @staticmethod
    def _sanitize_filter(filter_str: str) -> str:
        dangerous = [";", "|", "&", "$", "`", "(", ")", "{", "}", "[", "]"]
        for char in dangerous:
            if char in filter_str:
                raise ValueError(f"Unsafe character in FFmpeg filter: {char}")
        return filter_str
