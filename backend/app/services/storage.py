import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO
from app.core.config import settings


class StorageService:
    def __init__(self):
        if settings.storage_type == "local":
            self.local_path = Path(settings.storage_local_path)
            self.local_path.mkdir(parents=True, exist_ok=True)
        elif settings.storage_type == "s3":
            import boto3
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.storage_s3_region,
                endpoint_url=settings.storage_s3_endpoint or None,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            self.s3_bucket = settings.storage_s3_bucket
        elif settings.storage_type == "minio":
            from minio import Minio
            self.minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=False,
            )
            self.minio_bucket = settings.minio_bucket
            self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.minio_client.bucket_exists(self.minio_bucket):
                self.minio_client.make_bucket(self.minio_bucket)
        except Exception:
            pass

    def _get_storage_path(self, project_id: uuid.UUID, filename: str) -> str:
        return f"projects/{project_id}/{uuid.uuid4()}_{filename}"

    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        project_id: uuid.UUID,
        content_type: Optional[str] = None,
    ) -> tuple[str, int]:
        storage_path = self._get_storage_path(project_id, filename)

        if settings.storage_type == "local":
            full_path = self.local_path / storage_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, "wb") as f:
                content = await file.read()
                await f.write(content)
                file_size = len(content)
            return storage_path, file_size

        elif settings.storage_type == "minio":
            file.seek(0)
            file_size = len(file.read())
            file.seek(0)
            self.minio_client.put_object(
                self.minio_bucket,
                storage_path,
                file,
                length=file_size,
                content_type=content_type or "application/octet-stream",
            )
            return storage_path, file_size

        elif settings.storage_type == "s3":
            file.seek(0)
            file_size = len(file.read())
            file.seek(0)
            self.s3_client.upload_fileobj(
                file,
                self.s3_bucket,
                storage_path,
                ExtraArgs={"ContentType": content_type or "application/octet-stream"},
            )
            return storage_path, file_size

        raise ValueError(f"Unsupported storage type: {settings.storage_type}")

    async def get_file(self, storage_path: str) -> Optional[bytes]:
        if settings.storage_type == "local":
            full_path = self.local_path / storage_path
            if not full_path.exists():
                return None
            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()

        elif settings.storage_type == "minio":
            try:
                response = self.minio_client.get_object(self.minio_bucket, storage_path)
                return response.read()
            except Exception:
                return None

        elif settings.storage_type == "s3":
            try:
                from io import BytesIO
                buffer = BytesIO()
                self.s3_client.download_fileobj(self.s3_bucket, storage_path, buffer)
                return buffer.getvalue()
            except Exception:
                return None

        return None

    def get_file_url(self, storage_path: str) -> Optional[str]:
        if settings.storage_type == "local":
            return f"/files/{storage_path}"

        elif settings.storage_type == "minio":
            return f"http://{settings.minio_endpoint}/{self.minio_bucket}/{storage_path}"

        elif settings.storage_type == "s3":
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": storage_path},
                ExpiresIn=3600,
            )

        return None

    async def delete_file(self, storage_path: str) -> bool:
        try:
            if settings.storage_type == "local":
                full_path = self.local_path / storage_path
                if full_path.exists():
                    full_path.unlink()
                return True

            elif settings.storage_type == "minio":
                self.minio_client.remove_object(self.minio_bucket, storage_path)
                return True

            elif settings.storage_type == "s3":
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=storage_path)
                return True
        except Exception:
            return False
