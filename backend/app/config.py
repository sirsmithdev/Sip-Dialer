"""
Application configuration settings using Pydantic Settings.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = "SIP Auto-Dialer"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: str = "postgresql+asyncpg://autodialer:autodialer_secret@localhost:5432/autodialer"

    @property
    def async_database_url(self) -> str:
        """Get database URL with asyncpg driver for async SQLAlchemy."""
        url = self.database_url
        # Handle DO App Platform postgres:// or postgresql:// URLs
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Get database URL with psycopg2 driver for sync SQLAlchemy."""
        url = self.database_url
        # Handle various postgres URL formats
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        elif "+asyncpg" in url:
            url = url.replace("+asyncpg", "", 1)
        return url

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = "redis://localhost:6379/0"

    # ==========================================================================
    # JWT Authentication
    # ==========================================================================
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ==========================================================================
    # S3-Compatible Storage (MinIO for dev, DO Spaces for prod)
    # ==========================================================================
    # For local development with MinIO:
    #   S3_ENDPOINT=localhost:9000, S3_SECURE=false
    # For Digital Ocean Spaces:
    #   S3_ENDPOINT=nyc3.digitaloceanspaces.com, S3_SECURE=true
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_secure: bool = False
    s3_bucket: str = "audio-files"
    s3_bucket_recordings: str = "call-recordings"
    s3_region: str = "us-east-1"  # For DO Spaces, use nyc3, sfo3, etc.

    # Legacy MinIO aliases (for backward compatibility)
    @property
    def minio_endpoint(self) -> str:
        return self.s3_endpoint

    @property
    def minio_access_key(self) -> str:
        return self.s3_access_key

    @property
    def minio_secret_key(self) -> str:
        return self.s3_secret_key

    @property
    def minio_secure(self) -> bool:
        return self.s3_secure

    @property
    def minio_bucket_audio(self) -> str:
        return self.s3_bucket

    @property
    def minio_bucket_recordings(self) -> str:
        return self.s3_bucket_recordings

    # ==========================================================================
    # Default SIP Settings (configurable via UI)
    # ==========================================================================
    sip_server: str = "192.168.1.100"
    sip_port: int = 5060
    sip_username: str = "autodialer"
    sip_password: str = ""
    sip_transport: str = "UDP"
    sip_registration_required: bool = True
    sip_keepalive_interval: int = 30

    # ==========================================================================
    # RTP Settings
    # ==========================================================================
    rtp_port_start: int = 10000
    rtp_port_end: int = 20000

    # ==========================================================================
    # FastAGI Server
    # ==========================================================================
    agi_host: str = "0.0.0.0"
    agi_port: int = 4573

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: str = "http://localhost,http://localhost:3000"

    # ==========================================================================
    # Encryption
    # ==========================================================================
    encryption_key: str = "change-me-generate-a-secure-key"

    # ==========================================================================
    # SMTP Email Settings (defaults, can be overridden per-organization in DB)
    # ==========================================================================
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@autodialer.local"
    smtp_from_name: str = "SIP Auto-Dialer"
    smtp_use_tls: bool = True
    smtp_enabled: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
