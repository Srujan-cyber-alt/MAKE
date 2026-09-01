import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import (
    String, Text, Enum as SQLEnum, Float, Integer, Boolean,
    DateTime, ForeignKey, JSON, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AssetType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    REFERENCE = "reference"
    GENERATED = "generated"


class AssetStatus(str, enum.Enum):
    UPLOADING = "uploading"
    READY = "ready"
    PROCESSING = "processing"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    GENERATING = "generating"
    EDITING = "editing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    EDIT = "edit"
    VFX = "vfx"
    RENDER = "render"
    EXPORT = "export"


class ProviderStatus(str, enum.Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    ERROR = "error"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects: Mapped[List["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    jobs: Mapped[List["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    assets: Mapped[List["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[List["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    versions: Mapped[List["ProjectVersion"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    timelines: Mapped[List["Timeline"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="versions")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_url: Mapped[Optional[str]] = mapped_column(String(1024))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    fps: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[AssetStatus] = mapped_column(SQLEnum(AssetStatus), default=AssetStatus.UPLOADING)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    job_type: Mapped[JobType] = mapped_column(SQLEnum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    provider: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    prompt: Mapped[Optional[str]] = mapped_column(Text)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    input_assets: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    output_assets: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="jobs")
    project: Mapped[Optional["Project"]] = relationship(back_populates="jobs")


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    fps: Mapped[float] = mapped_column(Float, default=30.0)
    resolution: Mapped[Optional[str]] = mapped_column(String(50))
    tracks: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="timelines")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    api_base: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ProviderStatus] = mapped_column(SQLEnum(ProviderStatus), default=ProviderStatus.INACTIVE)
    capabilities: Mapped[List[str]] = mapped_column(JSON, default=list)
    rate_limits: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EditOperation(Base):
    __tablename__ = "edit_operations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
