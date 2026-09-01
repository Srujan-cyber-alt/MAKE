from typing import List, Dict, Any, Optional
from app.schemas.transformation import MaskRequest, MaskResponse
from datetime import datetime
from app.services.video_processing import video_processing_service
import uuid


class MaskEngine:
    MASK_TYPES = {
        "person": {"color": "green", "label": "Person"},
        "object": {"color": "blue", "label": "Object"},
        "background": {"color": "black", "label": "Background"},
        "face": {"color": "yellow", "label": "Face"},
        "product": {"color": "magenta", "label": "Product"},
        "sky": {"color": "cyan", "label": "Sky"},
    }

    @staticmethod
    def create_mask(request: MaskRequest) -> MaskResponse:
        mask_id = str(uuid.uuid4())
        frames = MaskEngine._generate_placeholder_frames(request)
        metadata = MaskEngine._build_metadata(request)

        return MaskResponse(
            id=mask_id,
            asset_id=request.asset_id,
            mask_type=request.mask_type,
            frames=frames,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def _generate_placeholder_frames(request: MaskRequest) -> List[Dict[str, Any]]:
        mask_config = MaskEngine.MASK_TYPES.get(request.mask_type, {"color": "white", "label": "Custom"})
        frame = {
            "frame_number": 0,
            "format": "rgba",
            "color": mask_config["color"],
            "feather": request.feather,
            "expand": request.expand,
            "invert": request.invert,
            "parameters": request.parameters,
        }
        if request.frame_range:
            frame["frame_range"] = request.frame_range
        return [frame]

    @staticmethod
    def _build_metadata(request: MaskRequest) -> Dict[str, Any]:
        return {
            "mask_type": request.mask_type,
            "feather": request.feather,
            "expand": request.expand,
            "invert": request.invert,
            "frame_range": request.frame_range,
            "parameters": request.parameters,
            "generated_by": "mask_engine_v1",
            "note": "Placeholder mask. ML-based segmentation will be added in Phase 7+.",
        }

    @staticmethod
    def apply_mask_to_video(
        source_path: str,
        mask_frames: List[Dict[str, Any]],
        output_path: str,
        blend_mode: str = "normal",
    ) -> str:
        if not mask_frames:
            raise ValueError("No mask frames provided")

        mask_frame = mask_frames[0]
        color = mask_frame.get("color", "white")
        feather = mask_frame.get("feather", 0)
        expand = mask_frame.get("expand", 0)

        filter_parts = [
            f"color=c={color}:s=1920x1080[base]",
            f"[base]boxblur={feather}[mask]",
        ]

        if expand:
            filter_parts.append(f"[mask]scale=iw+{expand}:ih+{expand}[expanded]")
            filter_parts.append(f"[expanded]crop=1920:1080[mask]")

        if blend_mode == "normal":
            filter_parts.append("[0:v][mask]overlay=0:0:format=auto")
        elif blend_mode == "multiply":
            filter_parts.append("[0:v][mask]blend=all_mode=multiply")
        elif blend_mode == "screen":
            filter_parts.append("[0:v][mask]blend=all_mode=screen")
        elif blend_mode == "overlay":
            filter_parts.append("[0:v][mask]blend=all_mode=overlay")
        else:
            filter_parts.append("[0:v][mask]overlay=0:0:format=auto")

        filter_str = ";".join(filter_parts)

        return video_processing_service.apply_filter(source_path, filter_str, output_path)

    @staticmethod
    def invert_mask(mask_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        inverted = []
        for frame in mask_frames:
            new_frame = dict(frame)
            new_frame["invert"] = not frame.get("invert", False)
            inverted.append(new_frame)
        return inverted

    @staticmethod
    def feather_mask(mask_frames: List[Dict[str, Any]], radius: int) -> List[Dict[str, Any]]:
        if radius <= 0:
            return mask_frames
        result = []
        for frame in mask_frames:
            new_frame = dict(frame)
            new_frame["feather"] = frame.get("feather", 0) + radius
            result.append(new_frame)
        return result
