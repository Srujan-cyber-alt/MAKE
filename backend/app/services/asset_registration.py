from datetime import datetime
from typing import Optional, Dict, Any, List
from app.models.models import Asset, AssetType, AssetStatus
from app.services.storage import storage_service
from app.services.video_processing import VideoProcessingService


class AssetRegistrationService:
    def __init__(self):
        self.video_service = VideoProcessingService()

    async def register_generated_asset(
        self,
        db_session,
        project_id: str,
        file_path: str,
        generation_job_id: str,
        provider: str,
        model: str,
        prompt: str,
        shot_id: str = None,
        scene_id: str = None,
        plan_id: str = None,
        references: List[str] = None,
        generation_settings: Dict[str, Any] = None,
    ) -> Optional[Asset]:
        try:
            media_info = await self.video_service.inspect_media(file_path)
        except Exception:
            return None

        filename = os.path.basename(file_path)
        storage_path, file_size = await storage_service.upload_file(
            file_path=file_path,
            filename=filename,
            project_id=project_id,
            content_type="video/mp4",
        )

        asset = Asset(
            project_id=project_id,
            asset_type=AssetType.GENERATED,
            filename=filename,
            original_filename=filename,
            content_type="video/mp4",
            file_size=file_size,
            storage_path=storage_path,
            storage_url=storage_service.get_file_url(storage_path),
            duration_seconds=media_info.duration_seconds,
            width=media_info.width,
            height=media_info.height,
            fps=media_info.fps,
            status=AssetStatus.READY,
            asset_metadata={
                "generation_job_id": generation_job_id,
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "shot_id": shot_id,
                "scene_id": scene_id,
                "plan_id": plan_id,
                "references": references or [],
                "generation_settings": generation_settings or {},
                "codec_name": media_info.codec_name,
                "format_name": media_info.format_name,
                "bit_rate": media_info.bit_rate,
                "pixel_format": media_info.pixel_format,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )

        db_session.add(asset)
        await db_session.flush()
        await db_session.refresh(asset)
        return asset

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


import os
from sqlalchemy.ext.asyncio import AsyncSession

asset_registration_service = AssetRegistrationService()
