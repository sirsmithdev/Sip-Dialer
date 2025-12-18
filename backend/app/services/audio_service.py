"""
Audio service for managing audio files.
"""
import uuid
import logging
from datetime import timedelta
from typing import Optional, List, BinaryIO

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio import AudioFile, AudioFormat, AudioStatus
from app.schemas.audio import AudioFileCreate, AudioFileUpdate
from app.services.storage_service import storage_service
from app.config import settings

logger = logging.getLogger(__name__)

# MIME type mapping for audio formats
MIME_TYPES = {
    AudioFormat.MP3: "audio/mpeg",
    AudioFormat.WAV: "audio/wav",
    AudioFormat.GSM: "audio/gsm",
    AudioFormat.ULAW: "audio/basic",
    AudioFormat.ALAW: "audio/alaw",
}

# File extension to format mapping
EXTENSION_TO_FORMAT = {
    ".mp3": AudioFormat.MP3,
    ".wav": AudioFormat.WAV,
    ".gsm": AudioFormat.GSM,
    ".ulaw": AudioFormat.ULAW,
    ".alaw": AudioFormat.ALAW,
}


def get_format_from_filename(filename: str) -> Optional[AudioFormat]:
    """Get audio format from filename extension."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return EXTENSION_TO_FORMAT.get(f".{ext}")


class AudioService:
    """Service for audio file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bucket = settings.minio_bucket_audio

    async def get_by_id(self, audio_id: str) -> Optional[AudioFile]:
        """Get audio file by ID."""
        result = await self.db.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self,
        audio_id: str,
        organization_id: str
    ) -> Optional[AudioFile]:
        """Get audio file by ID and organization."""
        result = await self.db.execute(
            select(AudioFile).where(
                AudioFile.id == audio_id,
                AudioFile.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[AudioStatus] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[AudioFile], int]:
        """
        List audio files for an organization with pagination.

        Returns:
            Tuple of (audio files list, total count)
        """
        query = select(AudioFile).where(
            AudioFile.organization_id == organization_id
        )

        # Apply filters
        if status:
            query = query.where(AudioFile.status == status)
        if is_active is not None:
            query = query.where(AudioFile.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(AudioFile.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        audio_files = result.scalars().all()

        return list(audio_files), total

    async def upload(
        self,
        organization_id: str,
        user_id: str,
        name: str,
        description: Optional[str],
        filename: str,
        file_data: BinaryIO,
        file_size: int
    ) -> AudioFile:
        """
        Upload an audio file.

        Args:
            organization_id: Organization ID
            user_id: User ID who uploaded
            name: Display name
            description: Optional description
            filename: Original filename
            file_data: File data to upload
            file_size: Size in bytes

        Returns:
            Created AudioFile record
        """
        # Determine format from filename
        audio_format = get_format_from_filename(filename)
        if not audio_format:
            raise ValueError(f"Unsupported audio format: {filename}")

        # Generate unique storage path
        file_id = str(uuid.uuid4())
        ext = filename.rsplit(".", 1)[-1].lower()
        storage_path = f"{organization_id}/{file_id}/original.{ext}"

        # Create database record with UPLOADING status
        audio_file = AudioFile(
            name=name,
            description=description,
            organization_id=organization_id,
            original_filename=filename,
            original_format=audio_format,
            file_size_bytes=file_size,
            storage_path=storage_path,
            storage_bucket=self.bucket,
            status=AudioStatus.UPLOADING,
            uploaded_by_id=user_id,
        )
        self.db.add(audio_file)
        await self.db.commit()
        await self.db.refresh(audio_file)

        try:
            # Upload to MinIO
            content_type = MIME_TYPES.get(audio_format, "application/octet-stream")
            storage_service.upload_file(
                bucket_name=self.bucket,
                object_name=storage_path,
                file_data=file_data,
                file_size=file_size,
                content_type=content_type,
            )

            # Update status to PROCESSING (transcoding will happen async)
            audio_file.status = AudioStatus.PROCESSING
            await self.db.commit()
            await self.db.refresh(audio_file)

            logger.info(f"Uploaded audio file {audio_file.id}: {filename}")
            return audio_file

        except Exception as e:
            # Update status to FAILED
            audio_file.status = AudioStatus.FAILED
            audio_file.error_message = str(e)
            await self.db.commit()
            logger.error(f"Failed to upload audio file: {e}")
            raise

    async def update(
        self,
        audio_file: AudioFile,
        update_data: AudioFileUpdate
    ) -> AudioFile:
        """Update audio file metadata."""
        data = update_data.model_dump(exclude_unset=True)

        for field, value in data.items():
            setattr(audio_file, field, value)

        await self.db.commit()
        await self.db.refresh(audio_file)
        return audio_file

    async def update_status(
        self,
        audio_file: AudioFile,
        status: AudioStatus,
        error_message: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        transcoded_paths: Optional[dict] = None
    ) -> AudioFile:
        """Update audio file processing status and metadata."""
        audio_file.status = status

        if error_message:
            audio_file.error_message = error_message
        if duration_seconds is not None:
            audio_file.duration_seconds = duration_seconds
        if sample_rate is not None:
            audio_file.sample_rate = sample_rate
        if channels is not None:
            audio_file.channels = channels
        if transcoded_paths is not None:
            audio_file.transcoded_paths = transcoded_paths

        await self.db.commit()
        await self.db.refresh(audio_file)
        return audio_file

    def get_download_url(
        self,
        audio_file: AudioFile,
        format: str = "original",
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Get presigned download URL for audio file.

        Args:
            audio_file: AudioFile record
            format: Format to download (original, wav, gsm, ulaw, alaw)
            expires: URL expiration time

        Returns:
            Presigned URL
        """
        if format == "original":
            object_name = audio_file.storage_path
        elif audio_file.transcoded_paths and format in audio_file.transcoded_paths:
            object_name = audio_file.transcoded_paths[format]
        else:
            # Fallback to original if transcoded version not available
            object_name = audio_file.storage_path

        return storage_service.get_presigned_url(
            bucket_name=audio_file.storage_bucket,
            object_name=object_name,
            expires=expires,
        )

    async def delete(self, audio_file: AudioFile) -> None:
        """Delete audio file from storage and database."""
        try:
            # Delete original file
            storage_service.delete_file(
                bucket_name=audio_file.storage_bucket,
                object_name=audio_file.storage_path,
            )

            # Delete transcoded versions
            if audio_file.transcoded_paths:
                for path in audio_file.transcoded_paths.values():
                    try:
                        storage_service.delete_file(
                            bucket_name=audio_file.storage_bucket,
                            object_name=path,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete transcoded file {path}: {e}")

        except Exception as e:
            logger.warning(f"Failed to delete storage files: {e}")

        # Delete database record
        await self.db.delete(audio_file)
        await self.db.commit()
        logger.info(f"Deleted audio file {audio_file.id}")

    def download_file(self, audio_file: AudioFile, format: str = "original") -> bytes:
        """
        Download audio file content.

        Args:
            audio_file: AudioFile record
            format: Format to download

        Returns:
            File content as bytes
        """
        if format == "original":
            object_name = audio_file.storage_path
        elif audio_file.transcoded_paths and format in audio_file.transcoded_paths:
            object_name = audio_file.transcoded_paths[format]
        else:
            object_name = audio_file.storage_path

        return storage_service.download_file(
            bucket_name=audio_file.storage_bucket,
            object_name=object_name,
        )
