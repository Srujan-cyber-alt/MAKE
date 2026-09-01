# MAKE AI Video

Production-grade AI video generation, editing, and transformation platform.

## Architecture

```
make-ai-video/
├── backend/                 # FastAPI async backend
│   ├── app/
│   │   ├── core/           # Config, database, auth
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── routers/        # API endpoints
│   │   ├── providers/      # Video provider adapters
│   │   └── services/       # Storage, orchestration
│   ├── tests/              # pytest tests
│   └── .env.example        # Environment configuration
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client
│   │   └── stores/         # State management
│   └── .env.example
└── package.json            # Workspace root
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
alembic upgrade head
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
- JWT-based authentication
- Provider-agnostic video generation abstraction
- Async job orchestration with retry logic
- Multi-backend storage abstraction (local, S3, MinIO)
- RESTful API with FastAPI

### Phase 2: Core Video (COMPLETE)
- Text-to-video workflow
- Image-to-video workflow
- Multi-reference support
- Real provider adapters (Runway, Pika)
- Job lifecycle management
- Project and asset management

### Phase 3: AI Editing (COMPLETE)
- Natural-language command interpreter
- Video editor UI
- Edit operation routing
- Quick command suggestions

### Phases 4-8: Future Work
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
