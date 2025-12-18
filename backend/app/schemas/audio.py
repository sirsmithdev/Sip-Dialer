"""
Audio file schemas.
"""
from datetime import datetime
from typing import Optional, Dict

from pydantic import BaseModel, Field

from app.models.audio import AudioFormat, AudioStatus


class AudioFileBase(BaseModel):
    """Base audio file schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the audio file")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")


class AudioFileCreate(AudioFileBase):
    """Schema for creating audio file metadata (file uploaded separately)."""
    pass


class AudioFileUpdate(BaseModel):
    """Schema for updating audio file metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class AudioFileResponse(AudioFileBase):
    """Audio file response schema."""
    id: str
    organization_id: str

    # File info
    original_filename: str
    original_format: AudioFormat
    file_size_bytes: int

    # Audio metadata
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None

    # Status
    status: AudioStatus
    error_message: Optional[str] = None
    is_active: bool

    # Available formats (after transcoding)
    transcoded_paths: Optional[Dict[str, str]] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    uploaded_by_id: Optional[str] = None

    class Config:
        from_attributes = True


class AudioFileListResponse(BaseModel):
    """Response for listing audio files."""
    items: list[AudioFileResponse]
    total: int
    page: int
    page_size: int


class AudioUploadResponse(BaseModel):
    """Response after uploading an audio file."""
    id: str
    name: str
    original_filename: str
    status: AudioStatus
    message: str


class AudioDownloadResponse(BaseModel):
    """Response with download URL for audio file."""
    id: str
    name: str
    format: str
    download_url: str
    expires_in_seconds: int = 3600
