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
    # MinIO / S3
    # ==========================================================================
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_audio: str = "audio-files"
    minio_bucket_recordings: str = "call-recordings"

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

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
