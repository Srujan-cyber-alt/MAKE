from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name, "version": "0.1.0"}


@router.get("/health/ready")
async def readiness():
    return {"status": "ready"}


@router.get("/health/live")
async def liveness():
    return {"status": "alive"}
