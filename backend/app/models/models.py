import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from sqlalchemy import (
    String, Text, Enum as SQLEnum, Float, Integer, Boolean,
    DateTime, ForeignKey, JSON
)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    project_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    assets: Mapped[List["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[List["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    versions: Mapped[List["ProjectVersion"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    timelines: Mapped[List["Timeline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reference_assets: Mapped[List["ReferenceAsset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    director_plans: Mapped[List["DirectorPlan"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="versions")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
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
    asset_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("director_plans.id", ondelete="SET NULL"))
    scene_id: Mapped[Optional[str]] = mapped_column(String(100))
    shot_id: Mapped[Optional[str]] = mapped_column(String(100))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    transformation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transformations.id", ondelete="SET NULL"), index=True)
    parent_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), index=True)
    stage: Mapped[Optional[str]] = mapped_column(String(100))
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
    director_plan: Mapped[Optional["DirectorPlan"]] = relationship(back_populates="generation_jobs")

    transformation_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    parent_job_id: Mapped[Optional[str]] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    children: Mapped[List["Job"]] = relationship("Job", remote_side="Job.id")


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    api_base: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ProviderStatus] = mapped_column(SQLEnum(ProviderStatus), default=ProviderStatus.INACTIVE)
    capabilities: Mapped[List[str]] = mapped_column(JSON, default=list)
    rate_limits: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    provider_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EditOperation(Base):
    __tablename__ = "edit_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReferenceAsset(Base):
    __tablename__ = "reference_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    ref_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="reference_assets")


class DirectorPlan(Base):
    __tablename__ = "director_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    creative_concept: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    scenes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    asset_requirements: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    continuity_requirements: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    audio_requirements: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    export_requirements: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    generation_requirements: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="director_plans")
    generation_jobs: Mapped[List["Job"]] = relationship(back_populates="director_plan")


class TransformationStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transformation(Base):
    __tablename__ = "transformations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    result_asset_id: Mapped[Optional[str]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    operations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    references: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[TransformationStatus] = mapped_column(SQLEnum(TransformationStatus), default=TransformationStatus.PENDING)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_stage: Mapped[Optional[str]] = mapped_column(String(50))
    error: Mapped[Optional[str]] = mapped_column(Text)
    result_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TransformationOperationModel(Base):
    __tablename__ = "transformation_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    transformation_id: Mapped[str] = mapped_column(ForeignKey("transformations.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    references: Mapped[List[str]] = mapped_column(JSON, default=list)
    preserve_identity: Mapped[bool] = mapped_column(Boolean, default=False)
    preserve_background: Mapped[bool] = mapped_column(Boolean, default=False)
    strength: Mapped[float] = mapped_column(Float, default=0.8)
    seed: Mapped[Optional[int]] = mapped_column(Integer)
    frame_range: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    depends_on: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TransformationMask(Base):
    __tablename__ = "transformation_masks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    transformation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("transformations.id", ondelete="CASCADE"), nullable=True, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    mask_type: Mapped[str] = mapped_column(String(50), nullable=False)
    frame_range: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    feather: Mapped[float] = mapped_column(Float, default=2.0)
    expand: Mapped[int] = mapped_column(Integer, default=0)
    invert: Mapped[bool] = mapped_column(Boolean, default=False)
    storage_dir: Mapped[Optional[str]] = mapped_column(String(512))
    frame_paths: Mapped[List[str]] = mapped_column(JSON, default=list)
    mask_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
