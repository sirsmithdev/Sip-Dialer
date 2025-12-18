"""
Audio-related Celery tasks.
"""
import os
import tempfile
import subprocess
import logging
from typing import Dict, Any

from workers.celery_app import app

logger = logging.getLogger(__name__)


def get_db_session():
    """Get sync database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://autodialer:autodialer_secret@localhost:5432/autodialer"
    )
    # Convert async URL to sync
    sync_url = database_url.replace("+asyncpg", "")

    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


def get_storage_service():
    """Get storage service instance."""
    from minio import Minio

    return Minio(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


def get_audio_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract audio metadata using ffprobe.

    Returns:
        Dictionary with duration, sample_rate, channels
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"ffprobe failed: {result.stderr}")
            return {}

        import json
        data = json.loads(result.stdout)

        # Extract from format
        format_info = data.get("format", {})
        duration = float(format_info.get("duration", 0))

        # Extract from audio stream
        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

        sample_rate = int(audio_stream.get("sample_rate", 0))
        channels = int(audio_stream.get("channels", 0))

        return {
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
        }

    except subprocess.TimeoutExpired:
        logger.error("ffprobe timed out")
        return {}
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}


def transcode_to_wav_8khz(input_path: str, output_path: str) -> bool:
    """
    Transcode audio to WAV format suitable for telephony.

    Output: 8kHz, mono, 16-bit PCM WAV
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", input_path,
                "-ar", "8000",      # 8kHz sample rate
                "-ac", "1",         # Mono
                "-acodec", "pcm_s16le",  # 16-bit PCM
                "-f", "wav",
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg transcode failed: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg transcode timed out")
        return False
    except Exception as e:
        logger.error(f"Transcode error: {e}")
        return False


def transcode_to_ulaw(input_path: str, output_path: str) -> bool:
    """
    Transcode audio to u-law format (G.711 mu-law).

    Output: 8kHz, mono, u-law
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "8000",
                "-ac", "1",
                "-acodec", "pcm_mulaw",
                "-f", "mulaw",
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg ulaw transcode failed: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"ulaw transcode error: {e}")
        return False


def transcode_to_alaw(input_path: str, output_path: str) -> bool:
    """
    Transcode audio to a-law format (G.711 a-law).

    Output: 8kHz, mono, a-law
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "8000",
                "-ac", "1",
                "-acodec", "pcm_alaw",
                "-f", "alaw",
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg alaw transcode failed: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"alaw transcode error: {e}")
        return False


@app.task(bind=True, name="workers.tasks.audio_tasks.transcode_audio")
def transcode_audio(self, audio_file_id: str, target_formats: list = None):
    """
    Transcode audio file to telephony-compatible formats.

    This task:
    1. Downloads the original audio from MinIO
    2. Extracts metadata (duration, sample rate, channels)
    3. Transcodes to WAV (8kHz mono) for playback
    4. Uploads transcoded versions back to MinIO
    5. Updates the database record with status and metadata
    """
    if target_formats is None:
        target_formats = ["wav"]  # Default to WAV for telephony

    logger.info(f"Starting transcode for audio file {audio_file_id}")

    session = None
    temp_dir = None

    try:
        # Get database session
        session = get_db_session()

        # Import model here to avoid circular imports
        from app.models.audio import AudioFile, AudioStatus

        # Get audio file record
        audio_file = session.query(AudioFile).filter(AudioFile.id == audio_file_id).first()

        if not audio_file:
            logger.error(f"Audio file not found: {audio_file_id}")
            return {"status": "error", "message": "Audio file not found"}

        # Get storage client
        storage = get_storage_service()

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="audio_transcode_")

        # Download original file
        original_ext = audio_file.original_filename.rsplit(".", 1)[-1].lower()
        original_path = os.path.join(temp_dir, f"original.{original_ext}")

        logger.info(f"Downloading from {audio_file.storage_bucket}/{audio_file.storage_path}")

        response = storage.get_object(audio_file.storage_bucket, audio_file.storage_path)
        with open(original_path, "wb") as f:
            for chunk in response.stream(32 * 1024):
                f.write(chunk)
        response.close()
        response.release_conn()

        # Extract metadata
        metadata = get_audio_metadata(original_path)
        logger.info(f"Audio metadata: {metadata}")

        # Transcode to each format
        transcoded_paths = {}
        base_storage_path = audio_file.storage_path.rsplit("/", 1)[0]

        for fmt in target_formats:
            output_filename = f"transcoded.{fmt}"
            output_path = os.path.join(temp_dir, output_filename)

            logger.info(f"Transcoding to {fmt}")

            success = False
            if fmt == "wav":
                success = transcode_to_wav_8khz(original_path, output_path)
            elif fmt == "ulaw":
                success = transcode_to_ulaw(original_path, output_path)
            elif fmt == "alaw":
                success = transcode_to_alaw(original_path, output_path)
            else:
                logger.warning(f"Unknown format: {fmt}, skipping")
                continue

            if success and os.path.exists(output_path):
                # Upload transcoded file
                storage_object_path = f"{base_storage_path}/{output_filename}"

                with open(output_path, "rb") as f:
                    file_size = os.path.getsize(output_path)
                    storage.put_object(
                        bucket_name=audio_file.storage_bucket,
                        object_name=storage_object_path,
                        data=f,
                        length=file_size,
                        content_type=f"audio/{fmt}" if fmt != "wav" else "audio/wav"
                    )

                transcoded_paths[fmt] = storage_object_path
                logger.info(f"Uploaded transcoded {fmt} to {storage_object_path}")
            else:
                logger.error(f"Failed to transcode to {fmt}")

        # Update database record
        audio_file.status = AudioStatus.READY
        audio_file.transcoded_paths = transcoded_paths

        if metadata:
            if metadata.get("duration_seconds"):
                audio_file.duration_seconds = metadata["duration_seconds"]
            if metadata.get("sample_rate"):
                audio_file.sample_rate = metadata["sample_rate"]
            if metadata.get("channels"):
                audio_file.channels = metadata["channels"]

        session.commit()

        logger.info(f"Transcode complete for {audio_file_id}: {list(transcoded_paths.keys())}")

        return {
            "status": "success",
            "audio_file_id": audio_file_id,
            "formats": list(transcoded_paths.keys()),
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Transcode failed for {audio_file_id}: {e}")

        # Update status to failed
        if session:
            try:
                from app.models.audio import AudioFile, AudioStatus
                audio_file = session.query(AudioFile).filter(AudioFile.id == audio_file_id).first()
                if audio_file:
                    audio_file.status = AudioStatus.FAILED
                    audio_file.error_message = str(e)[:500]
                    session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update status: {db_error}")

        return {
            "status": "error",
            "audio_file_id": audio_file_id,
            "message": str(e)
        }

    finally:
        # Cleanup
        if session:
            session.close()

        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")


@app.task(bind=True, name="workers.tasks.audio_tasks.analyze_audio")
def analyze_audio(self, audio_file_id: str):
    """
    Analyze audio file for duration, format, and quality.

    This task extracts metadata from an audio file without transcoding.
    """
    logger.info(f"Analyzing audio file {audio_file_id}")

    session = None
    temp_dir = None

    try:
        session = get_db_session()

        from app.models.audio import AudioFile

        audio_file = session.query(AudioFile).filter(AudioFile.id == audio_file_id).first()

        if not audio_file:
            return {"status": "error", "message": "Audio file not found"}

        # Get storage client
        storage = get_storage_service()

        # Create temp directory and download file
        temp_dir = tempfile.mkdtemp(prefix="audio_analyze_")
        original_ext = audio_file.original_filename.rsplit(".", 1)[-1].lower()
        original_path = os.path.join(temp_dir, f"original.{original_ext}")

        response = storage.get_object(audio_file.storage_bucket, audio_file.storage_path)
        with open(original_path, "wb") as f:
            for chunk in response.stream(32 * 1024):
                f.write(chunk)
        response.close()
        response.release_conn()

        # Extract metadata
        metadata = get_audio_metadata(original_path)

        if metadata:
            if metadata.get("duration_seconds"):
                audio_file.duration_seconds = metadata["duration_seconds"]
            if metadata.get("sample_rate"):
                audio_file.sample_rate = metadata["sample_rate"]
            if metadata.get("channels"):
                audio_file.channels = metadata["channels"]
            session.commit()

        return {
            "status": "analyzed",
            "audio_file_id": audio_file_id,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Analysis failed for {audio_file_id}: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        if session:
            session.close()

        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


@app.task(bind=True, name="workers.tasks.audio_tasks.cleanup_temp_files")
def cleanup_temp_files(self):
    """Clean up temporary audio files."""
    import glob
    import time

    temp_base = tempfile.gettempdir()
    pattern = os.path.join(temp_base, "audio_*")

    files_removed = 0
    cutoff = time.time() - 3600  # 1 hour old

    for path in glob.glob(pattern):
        try:
            if os.path.getmtime(path) < cutoff:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                files_removed += 1
        except Exception as e:
            logger.warning(f"Failed to remove {path}: {e}")

    return {"status": "cleaned", "files_removed": files_removed}
