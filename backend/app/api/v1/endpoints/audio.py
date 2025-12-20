"""
Audio file management endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, require_roles
from app.schemas.audio import (
    AudioFileResponse,
    AudioFileUpdate,
    AudioFileListResponse,
    AudioUploadResponse,
    AudioDownloadResponse,
)
from app.services.audio_service import AudioService
from app.models.user import User, UserRole
from app.models.audio import AudioStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".gsm", ".ulaw", ".alaw"}


def validate_audio_file(filename: str, file_size: int) -> None:
    """Validate uploaded audio file."""
    # Check extension
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )


@router.get("", response_model=AudioFileListResponse)
async def list_audio_files(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[AudioStatus] = Query(None, alias="status", description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """
    List audio files for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_files, total = await service.list_by_organization(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        is_active=is_active,
    )

    return AudioFileListResponse(
        items=audio_files,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    file: UploadFile = File(..., description="Audio file (MP3 or WAV)"),
    name: str = Form(..., min_length=1, max_length=255, description="Display name"),
    description: Optional[str] = Form(None, max_length=500, description="Optional description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Upload an audio file for use in campaigns.

    Supports MP3 and WAV formats. Files are automatically converted to
    telephony-compatible formats (WAV 8kHz mono) for playback during calls.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    # Read file content to get size
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file
    validate_audio_file(file.filename or "unknown", file_size)

    # Reset file position for upload
    await file.seek(0)

    service = AudioService(db)

    try:
        audio_file = await service.upload(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            name=name,
            description=description,
            filename=file.filename or "audio",
            file_data=file.file,
            file_size=file_size,
        )

        # Trigger async transcoding task
        from workers.tasks.audio_tasks import transcode_audio
        transcode_audio.delay(str(audio_file.id))

        return AudioUploadResponse(
            id=audio_file.id,
            name=audio_file.name,
            original_filename=audio_file.original_filename,
            status=audio_file.status,
            message="Audio file uploaded successfully. Transcoding in progress.",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to upload audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload audio file"
        )


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio_file(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """
    Get audio file details by ID.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_file = await service.get_by_id_and_org(audio_id, current_user.organization_id)

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    return audio_file


@router.patch("/{audio_id}", response_model=AudioFileResponse)
async def update_audio_file(
    audio_id: str,
    update_data: AudioFileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Update audio file metadata.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_file = await service.get_by_id_and_org(audio_id, current_user.organization_id)

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    audio_file = await service.update(audio_file, update_data)
    return audio_file


@router.get("/{audio_id}/download", response_model=AudioDownloadResponse)
async def get_audio_download_url(
    audio_id: str,
    format: str = Query("original", description="Audio format: original, wav, gsm, ulaw, alaw"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """
    Get a presigned download URL for an audio file.

    The URL is valid for 1 hour.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_file = await service.get_by_id_and_org(audio_id, current_user.organization_id)

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    if audio_file.status != AudioStatus.READY and format != "original":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is not ready. Transcoded formats not available."
        )

    try:
        download_url = service.get_download_url(audio_file, format=format)

        return AudioDownloadResponse(
            id=audio_file.id,
            name=audio_file.name,
            format=format,
            download_url=download_url,
            expires_in_seconds=3600,
        )
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


@router.get("/{audio_id}/stream")
async def stream_audio_file(
    audio_id: str,
    format: str = Query("original", description="Audio format: original, wav, gsm, ulaw, alaw"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    """
    Stream audio file content directly.

    This endpoint returns the audio file content for playback in browser.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_file = await service.get_by_id_and_org(audio_id, current_user.organization_id)

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    try:
        file_content = service.download_file(audio_file, format=format)

        # Determine content type
        # Note: original_format is stored as a string in the database
        original_format_str = audio_file.original_format if isinstance(audio_file.original_format, str) else audio_file.original_format.value
        content_types = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "gsm": "audio/gsm",
            "ulaw": "audio/basic",
            "alaw": "audio/alaw",
            "original": "audio/mpeg" if original_format_str == "mp3" else "audio/wav",
        }
        content_type = content_types.get(format, "application/octet-stream")

        return StreamingResponse(
            iter([file_content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{audio_file.name}.{format if format != "original" else original_format_str}"',
                "Content-Length": str(len(file_content)),
            }
        )
    except Exception as e:
        logger.error(f"Failed to stream audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream audio file"
        )


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_file(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Delete an audio file.

    This permanently removes the file from storage.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = AudioService(db)
    audio_file = await service.get_by_id_and_org(audio_id, current_user.organization_id)

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    try:
        await service.delete(audio_file)
    except IntegrityError as e:
        logger.warning(f"Cannot delete audio file {audio_id}: still in use by campaigns")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete audio file: it is currently being used by one or more campaigns. Please remove it from all campaigns first."
        )
