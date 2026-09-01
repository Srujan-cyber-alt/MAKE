from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.models import UserRole, ProjectStatus, JobStatus, JobType, AssetType, AssetStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    status: ProjectStatus
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetBase(BaseModel):
    asset_type: AssetType
    filename: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetResponse(AssetBase):
    id: UUID
    project_id: UUID
    storage_path: str
    storage_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: AssetStatus
    file_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    job_type: JobType = JobType.TEXT_TO_VIDEO
    provider: Optional[str] = None
    model: Optional[str] = None
    duration_seconds: Optional[float] = Field(None, ge=1, le=120)
    width: Optional[int] = Field(None, ge=256, le=4096)
    height: Optional[int] = Field(None, ge=256, le=4096)
    fps: Optional[int] = Field(None, ge=1, le=60)
    aspect_ratio: Optional[str] = None
    seed: Optional[int] = None
    guidance_scale: Optional[float] = Field(None, ge=1, le=30)
    input_asset_ids: Optional[List[UUID]] = None
    reference_images: Optional[List[Dict[str, Any]]] = None
    parameters: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    job_type: JobType
    status: JobStatus
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    input_assets: Optional[List[Dict[str, Any]]] = None
    output_assets: Optional[List[Dict[str, Any]]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EditOperationRequest(BaseModel):
    operation_type: str
    parameters: Dict[str, Any]


class TimelineBase(BaseModel):
    name: str
    duration_seconds: Optional[float] = None
    fps: float = 30.0
    resolution: Optional[str] = None
    tracks: List[Dict[str, Any]]
    settings: Optional[Dict[str, Any]] = None


class TimelineCreate(TimelineBase):
    pass


class TimelineResponse(TimelineBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderResponse(BaseModel):
    id: UUID
    name: str
    provider_type: str
    api_base: str
    status: str
    capabilities: List[str]
    last_health_check: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommandInterpretRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = None


class CommandInterpretResponse(BaseModel):
    operations: List[Dict[str, Any]]
    confidence: float
    requires_clarification: bool
    clarification_questions: Optional[List[str]] = None
