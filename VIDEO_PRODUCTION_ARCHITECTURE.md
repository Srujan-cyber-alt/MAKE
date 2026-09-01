# MAKE AI VIDEO — PRODUCTION ARCHITECTURE
## Job #1: Video Generation + Video Editing + Video Transformation

============================================================
SYSTEM OVERVIEW
============================================================

MAKE AI Video is a production-grade AI video platform built on:

- **Backend**: FastAPI async Python service
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 async ORM
- **Cache/Queue**: Redis 7+ (optional, for scaling)
- **Storage**: Local filesystem, S3, or MinIO
- **Video Processing**: FFmpeg (local operations)
- **AI Providers**: Runway ML, Pika (pluggable via VideoProviderAdapter)
- **Job Orchestration**: Async in-process with worker abstraction (upgradeable to Celery)

============================================================
ARCHITECTURAL LAYERS
============================================================

1. **API Layer** (`app/routers/`)
   - RESTful endpoints under `/api/v1`
   - Authentication via JWT
   - Rate limiting via SlowAPI
   - CORS configured per environment

2. **Service Layer** (`app/services/`)
   - `storage.py`: Multi-backend storage abstraction
   - `orchestrator.py`: Job queue processing
   - `video_processing.py`: FFmpeg-based video operations
   - `redis_service.py`: Redis caching/queue preparation
   - `worker.py`: Worker abstraction for job execution

3. **Provider Layer** (`app/providers/`)
   - `base.py`: VideoProviderAdapter interface
   - `runway.py`: Runway ML provider
   - `pika.py`: Pika provider
   - `test_provider.py`: Deterministic test provider
   - `registry.py`: Provider/model registry with capability discovery

4. **Data Layer** (`app/models/`, `app/core/database.py`)
   - SQLAlchemy async ORM
   - UUID primary keys
   - JSON columns for flexible metadata
   - Alembic migrations

5. **Frontend Layer** (`frontend/src/`)
   - React 18 with hooks
   - React Router for navigation
   - React Query for data fetching
   - Zustand for auth state
   - Tailwind CSS for styling

============================================================
DATA MODEL
============================================================

**Core Entities:**
- `User` — authentication, profile
- `Project` — video project container
- `Asset` — uploaded/generated media files
- `Job` — async generation/edit/processing tasks
- `Timeline` — edit timeline with tracks
- `ProjectVersion` — snapshots for version control
- `ReferenceAsset` — semantic reference assignments
- `EditOperation` — individual edit operations
- `Provider` — provider configuration (DB-backed)

============================================================
GENERATION PIPELINE
============================================================

```
User Request
    ↓
Validation (Pydantic schemas)
    ↓
Authentication (JWT)
    ↓
Project Ownership Check
    ↓
Asset Upload/Validation (FileValidator)
    ↓
Storage (StorageService)
    ↓
Job Creation (QUEUED)
    ↓
Orchestrator picks up job
    ↓
Provider Selection (ProviderRegistry)
    ↓
Model Selection (ModelInfo/ModelLimits)
    ↓
Submit to Provider (VideoProviderAdapter.submit_generation)
    ↓
Poll for Status (check_status)
    ↓
Retrieve Result (get_result)
    ↓
Store Output (StorageService)
    ↓
Update Job (COMPLETED)
    ↓
Create Project Version
    ↓
UI Display
```

============================================================
EDIT PIPELINE
============================================================

```
Natural Language Command
    ↓
AICommandInterpreter
    ↓
Structured EditOperation[]
    ↓
EditExecutor
    ↓
VideoProcessingService (FFmpeg)
    ↓
Output Asset
    ↓
New Project Version
    ↓
UI Display
```

============================================================
PROVIDER ABSTRACTION
============================================================

All providers implement `VideoProviderAdapter`:
- `health_check()` — provider availability
- `submit_generation(request, model_id)` — start generation
- `check_status(provider_job_id)` — poll status
- `cancel_job(provider_job_id)` — cancel generation
- `get_result(provider_job_id)` — retrieve final result
- `get_capabilities()` — what the provider supports
- `get_supported_models()` — available models with limits

Provider registry enables:
- Capability-based discovery
- Model metadata lookup
- Multi-provider failover (future)

============================================================
STORAGE ABSTRACTION
============================================================

Storage backends:
- **Local**: Filesystem with path traversal protection
- **S3**: AWS S3 or compatible
- **MinIO**: Self-hosted S3-compatible storage

Configuration via `STORAGE_TYPE` environment variable.

============================================================
SECURITY MODEL
============================================================

- JWT authentication with bcrypt password hashing
- Project ownership enforced on all project-level operations
- Asset ownership enforced via project ownership
- Rate limiting on auth, generation, upload endpoints
- File upload validation (MIME, size, extension)
- Path traversal protection for local file serving
- No secrets committed to repository
- Environment-based configuration

============================================================
SCALABILITY PATH
============================================================

Current: In-process async orchestrator
→ Future: Celery + Redis workers
- JobExecutor abstraction already in place
- Provider/storage/worker separation complete
- Redis service prepared for distributed queue
