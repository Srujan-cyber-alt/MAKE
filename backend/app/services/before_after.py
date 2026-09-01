import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from app.services.video_processing import video_processing_service
from app.services.storage import storage_service
import logging

logger = logging.getLogger(__name__)


class BeforeAfterComparator:
    @staticmethod
    async def compare_videos(
        original_asset_id: str,
        result_asset_id: str,
        project_id: str,
        user_id: str,
        mode: str = "side_by_side",
    ) -> Dict[str, Any]:
        original_path = await BeforeAfterComparator._resolve_asset_path(original_asset_id, project_id, user_id)
        result_path = await BeforeAfterComparator._resolve_asset_path(result_asset_id, project_id, user_id)

        if not original_path or not Path(original_path).exists():
            raise HTTPException(status_code=404, detail="Original asset not found")
        if not result_path or not Path(result_path).exists():
            raise HTTPException(status_code=404, detail="Result asset not found")

        try:
            orig_info = await video_processing_service.inspect_media(original_path)
            result_info = await video_processing_service.inspect_media(result_path)
        except Exception as e:
            return {"error": f"Media inspection failed: {e}"}

        output_path = None
        if mode == "side_by_side":
            output_path = await BeforeAfterComparator._create_side_by_side(original_path, result_path)
        elif mode == "split_slider":
            output_path = await BeforeAfterComparator._create_split_slider(original_path, result_path)
        elif mode == "toggle":
            output_path = result_path

        return {
            "mode": mode,
            "original_path": original_path,
            "result_path": result_path,
            "comparison_path": output_path,
            "original_info": {
                "duration": getattr(orig_info, "duration_seconds", None),
                "resolution": (getattr(orig_info, "width", None), getattr(orig_info, "height", None)) if orig_info else None,
                "fps": getattr(orig_info, "fps", None),
            },
            "result_info": {
                "duration": getattr(result_info, "duration_seconds", None),
                "resolution": (getattr(result_info, "width", None), getattr(result_info, "height", None)) if result_info else None,
                "fps": getattr(result_info, "fps", None),
            },
        }

    @staticmethod
    async def _create_side_by_side(original_path: str, result_path: str) -> Optional[str]:
        output_path = f"/tmp/comparison_{Path(original_path).stem}_{Path(result_path).stem}.mp4"
        if not video_processing_service._check_ffmpeg():
            return None
        filter_str = (
            "[0:v]scale=iw/2:ih[left];"
            "[1:v]scale=iw/2:ih[right];"
            "[left][right]hstack=inputs=2"
        )
        try:
            await video_processing_service.apply_filter(original_path, filter_str, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Side-by-side comparison failed: {e}")
            return None

    @staticmethod
    async def _create_split_slider(original_path: str, result_path: str) -> Optional[str]:
        output_path = f"/tmp/comparison_slider_{Path(original_path).stem}_{Path(result_path).stem}.mp4"
        if not video_processing_service._check_ffmpeg():
            return None
        filter_str = (
            "[0:v][1:v]blend=all_mode=average:all_opacity=0.5"
        )
        try:
            await video_processing_service.apply_filter(original_path, filter_str, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Split slider comparison failed: {e}")
            return None

    @staticmethod
    async def _resolve_asset_path(asset_id: str, project_id: str, user_id: str) -> Optional[str]:
        try:
            return await storage_service.get_asset_path(asset_id, project_id, user_id)
        except Exception:
            return None
