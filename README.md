# MAKE AI Video

Production-grade AI video generation, editing, and transformation platform.

## Architecture

```
make-ai-video/
├── backend/                 # FastAPI async backend
│   ├── app/
│   │   ├── core/           # Config, database, auth, registry
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── routers/        # API endpoints
│   │   ├── providers/      # Video provider adapters + registry
│   │   └── services/       # Storage, orchestration
│   ├── tests/              # pytest tests
│   └── .env.example        # Environment configuration
├── frontend/               # React 18 + Vite + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client
│   │   └── stores/         # State management
│   └── .env.example
├── package.json            # Workspace root
├── ENGINEERING_REPORT.md   # Detailed engineering report
└── VIDEO_PHASE_2_AUDIT.md  # Phase 2 implementation audit
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Backend
```bash
cd backend
cp .env.example .env
# Edit .env with your database and provider credentials
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Key Features Implemented

### Phase 1: Foundation (COMPLETE)
- Production monorepo with workspace management
- Async PostgreSQL database with SQLAlchemy
- JWT authentication with refresh tokens
- Provider-agnostic video generation abstraction
- Async job orchestration with retry logic
- Multi-backend storage abstraction (local, S3, MinIO)
- RESTful API with FastAPI

### Phase 2: Core Video Completion (COMPLETE)
- Provider registry with capability discovery
- Model-level limits and metadata (ModelInfo/ModelLimits)
- Enhanced Runway and Pika adapters with model-aware submission
- Project versions API (create, list, restore)
- Project context API (persistent project memory)
- Reference assets API (multi-reference with semantic roles)
- Timeline API (CRUD operations)
- Local file serving with path traversal protection
- Improved Generate workspace with provider/model selection
- Multi-reference image upload with role assignment
- Structured prompt experience with natural language primary
- Image-to-video workflow
- Registration page
- New project page
- Fixed critical bugs (imports, circular dependencies, query params)
- Security fixes (path traversal, ownership checks)
- Comprehensive test suite

### Phases 3-8: Future Work
- Video-to-video transformation
- VFX engine
- Motion graphics
- Storyboard
- Creative director
- Social video factory
- Production hardening

## Testing

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

## Environment Variables

See `backend/.env.example` and `frontend/.env.example` for required configuration.

## License

Proprietary - MAKE AI
