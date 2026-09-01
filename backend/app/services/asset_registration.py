import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Asset, AssetType, AssetStatus
from app.services.storage import storage_service
from app.services.video_processing import VideoProcessingService


class AssetRegistrationService:
    def __init__(self):
        self.video_service = VideoProcessingService()

    async def register_generated_asset(
        self,
        job_id: str,
        project_id: str,
        user_id: str,
        storage_path: str,
        video_url: str,
        thumbnail_url: Optional[str],
        duration_seconds: Optional[float],
        width: Optional[int],
        height: Optional[int],
        fps: Optional[float],
        provider: str,
        model: str,
        prompt: str,
        shot_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        media_info: Optional[Any] = None,
    ) -> Optional[Asset]:
        try:
            if not media_info:
                local_path = os.path.join("/tmp/makeai_downloads", f"{job_id}.mp4")
                if os.path.exists(local_path):
                    try:
                        media_info = self.video_service.inspect_media(local_path)
                    except Exception:
                        media_info = None

            asset = Asset(
                project_id=project_id,
                asset_type=AssetType.GENERATED,
                filename=f"{job_id}.mp4",
                original_filename=f"generated_{job_id}.mp4",
                content_type="video/mp4",
                file_size=0,
                storage_path=storage_path,
                storage_url=video_url,
                thumbnail_path=thumbnail_url,
                duration_seconds=duration_seconds or (media_info.duration_seconds if media_info else None),
                width=width or (media_info.width if media_info else None),
                height=height or (media_info.height if media_info else None),
                fps=fps or (media_info.fps if media_info else None),
                status=AssetStatus.READY,
                asset_metadata={
                    "generation_job_id": job_id,
                    "provider": provider,
                    "model": model,
                    "prompt": prompt,
                    "shot_id": shot_id,
                    "scene_id": scene_id,
                    "plan_id": plan_id,
                    "references": [],
                    "generation_settings": {},
                    "codec_name": media_info.codec_name if media_info else None,
                    "format_name": media_info.format_name if media_info else None,
                    "bit_rate": media_info.bit_rate if media_info else None,
                    "pixel_format": media_info.pixel_format if media_info else None,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )

            async with AsyncSession() as session:
                session.add(asset)
                await session.commit()
                await session.refresh(asset)
            return asset
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Asset registration failed: {e}")
            return None

    def get_provenance(self, asset: Asset) -> Dict[str, Any]:
        metadata = asset.asset_metadata or {}
        return {
            "asset_id": asset.id,
            "project_id": asset.project_id,
            "generation_job_id": metadata.get("generation_job_id"),
            "provider": metadata.get("provider"),
            "model": metadata.get("model"),
            "prompt": metadata.get("prompt"),
            "shot_id": metadata.get("shot_id"),
            "scene_id": metadata.get("scene_id"),
            "plan_id": metadata.get("plan_id"),
            "references": metadata.get("references", []),
            "generation_settings": metadata.get("generation_settings", {}),
            "generated_at": metadata.get("generated_at"),
            "duration_seconds": asset.duration_seconds,
            "width": asset.width,
            "height": asset.height,
            "fps": asset.fps,
        }


asset_registration_service = AssetRegistrationService()
