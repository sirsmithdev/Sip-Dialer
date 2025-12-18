"""
Audio file model.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization


class AudioFormat(str, enum.Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    WAV = "wav"
    GSM = "gsm"
    ULAW = "ulaw"
    ALAW = "alaw"


class AudioStatus(str, enum.Enum):
    """Audio file processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AudioFile(Base, UUIDMixin, TimestampMixin):
    """Audio file model for storing campaign audio."""

    __tablename__ = "audio_files"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="audio_files"
    )

    # File info
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Using String instead of SQLEnum to match the database schema
    original_format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Storage paths (MinIO)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), default="audio")

    # Transcoded versions paths (JSON with format -> path mapping)
    transcoded_paths: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Audio metadata
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status - stored as string in DB, validated by AudioStatus enum
    status: Mapped[str] = mapped_column(String(20), default=AudioStatus.UPLOADING.value)
    error_message: Mapped[Optional[str]] = mapped_column(String(500))

    # Uploaded by
    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def get_playback_url(self, format: str = "mp3") -> Optional[str]:
        """Get URL for playing the audio file."""
        if self.transcoded_paths and format in self.transcoded_paths:
            return self.transcoded_paths[format]
        return self.storage_path

    def __repr__(self) -> str:
        return f"<AudioFile {self.name}>"
