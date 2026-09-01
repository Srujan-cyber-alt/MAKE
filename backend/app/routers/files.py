from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.services.storage import storage_service
from app.core.config import settings
import os

router = APIRouter()


@router.get("/{path:path}")
async def serve_file(path: str):
    if settings.storage_type != "local":
        raise HTTPException(status_code=400, detail="File serving only available for local storage")

    full_path = os.path.join(settings.storage_local_path, path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    safe_path = os.path.normpath(full_path)
    if not safe_path.startswith(os.path.normpath(settings.storage_local_path)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(safe_path)
