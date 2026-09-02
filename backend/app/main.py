from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter, rate_limit_exception_handler
from app.routers import auth, projects, assets, jobs, generation, editing, providers, health
from app.routers.project_extras import router as project_extras_router
from app.routers.timelines import router as timelines_router
from app.routers.files import router as files_router
from app.routers.director import router as director_router
from app.routers.transformation import router as transformation_router
from app.routers.phase7 import router as phase7_router
from app.routers.phase8 import router as phase8_router
from app.routers.phase9 import router as phase9_router
from app.routers.phase11 import router as phase11_router
from app.routers.phase12 import router as phase12_router
from app.routers.studio import router as studio_router
from app.routers.cinema import router as cinema_router
from app.routers.genesis import router as genesis_router
from app.services.transformation_engine import TransformationEngine
from app.core.database import init_db, async_session_maker
from app.services.orchestrator import JobOrchestrator
from app.services.storage import storage_service
from app.services.redis_service import redis_service
from app.providers import init_providers
from app.providers.registry import set_provider_registry
import sentry_sdk
import asyncio

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=0.1 if settings.app_env == "production" else 0.0,
    profiles_sample_rate=0.1 if settings.app_env == "production" else 0.0,
)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MAKE AI Video - Production-grade AI video generation, editing, and transformation API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(project_extras_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(generation.router, prefix="/api/v1/generation", tags=["generation"])
app.include_router(editing.router, prefix="/api/v1/editing", tags=["editing"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])
app.include_router(timelines_router, prefix="/api/v1/timelines", tags=["timelines"])
app.include_router(files_router, prefix="/api/v1/files", tags=["files"])
app.include_router(director_router, prefix="/api/v1/director", tags=["director"])
app.include_router(transformation_router, prefix="/api/v1/transformation", tags=["transformation"])
app.include_router(phase7_router, prefix="/api/v1/phase7", tags=["phase7"])
app.include_router(phase8_router, prefix="/api/v1/phase8", tags=["phase8"])
app.include_router(phase9_router, prefix="/api/v1/phase9", tags=["phase9"])
app.include_router(phase11_router, prefix="/api/v1/phase11", tags=["phase11"])
app.include_router(phase12_router, prefix="/api/v1/phase12", tags=["phase12"])
app.include_router(studio_router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(cinema_router, prefix="/api/v1/cinema", tags=["cinema"])
app.include_router(genesis_router, prefix="/api/v1/genesis", tags=["genesis"])

provider_registry = init_providers()
set_provider_registry(provider_registry)

orchestrator = JobOrchestrator(
    provider_registry=provider_registry,
    db_session_factory=async_session_maker,
    storage_service=storage_service,
)

from app.services.generation_engine import GenerationEngine

generation_engine = GenerationEngine(
    provider_registry=provider_registry,
    orchestrator=orchestrator,
    storage_service_instance=storage_service,
)

transformation_engine = TransformationEngine(
    provider_registry=provider_registry,
    db_session_factory=async_session_maker,
)


@app.get("/api/v1/")
async def root():
    return {"name": settings.app_name, "version": "0.1.0", "status": "operational"}


@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(orchestrator.start())


@app.on_event("shutdown")
async def shutdown():
    await orchestrator.stop()
    await redis_service.close()
