from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MAKE AI Video"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production-use-strong-random-key"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "postgresql+asyncpg://makeai:makeai_password@localhost:5432/makeai_video"

    redis_url: str = "redis://localhost:6379/0"

    storage_type: str = "local"
    storage_local_path: str = "/tmp/makeai-storage"
    storage_s3_bucket: str = ""
    storage_s3_region: str = ""
    storage_s3_endpoint: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "makeai-video"

    runway_api_key: str = ""
    runway_api_base: str = "https://api.runwayml.com/v1"
    pika_api_key: str = ""
    pika_api_base: str = "https://api.pika.art/v1"
    replicate_api_token: str = ""
    replicate_api_base: str = "https://api.replicate.com/v1"
    stability_api_key: str = ""
    stability_api_base: str = "https://api.stability.ai/v1"
    default_video_provider: str = "runway"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    rate_limit_default: str = "100/minute"
    rate_limit_generation: str = "10/hour"

    sentry_dsn: str = ""
    log_level: str = "INFO"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


settings = Settings()
