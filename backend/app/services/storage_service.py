"""
Storage service for MinIO/S3 operations.
"""
import io
import logging
from typing import Optional, BinaryIO
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for MinIO/S3 storage operations."""

    def __init__(self):
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        """Get or create MinIO client (works with both MinIO and DigitalOcean Spaces)."""
        if self._client is None:
            logger.info(f"Initializing storage client: endpoint={settings.s3_endpoint}, secure={settings.s3_secure}, region={settings.s3_region}")
            self._client = Minio(
                endpoint=settings.s3_endpoint,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                secure=settings.s3_secure,
                region=settings.s3_region,
            )
        return self._client

    def ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket {bucket_name}: {e}")
            raise

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket
            file_data: File-like object to upload
            file_size: Size of the file in bytes
            content_type: MIME type of the file

        Returns:
            The object path in the bucket
        """
        self.ensure_bucket(bucket_name)

        try:
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
            )
            logger.info(f"Uploaded {object_name} to bucket {bucket_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload bytes data to MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket
            data: Bytes to upload
            content_type: MIME type of the file

        Returns:
            The object path in the bucket
        """
        file_data = io.BytesIO(data)
        return self.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=file_data,
            file_size=len(data),
            content_type=content_type,
        )

    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket

        Returns:
            File contents as bytes
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            raise

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket
            expires: URL expiration time

        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires,
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted {object_name} from bucket {bucket_name}")
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise

    def file_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_file_info(self, bucket_name: str, object_name: str) -> dict:
        """
        Get file metadata from MinIO.

        Args:
            bucket_name: Name of the bucket
            object_name: Object path/name in the bucket

        Returns:
            Dictionary with file metadata
        """
        try:
            stat = self.client.stat_object(bucket_name, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }
        except S3Error as e:
            logger.error(f"Error getting file info: {e}")
            raise

    def health_check(self) -> bool:
        """
        Check if MinIO is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False


# Singleton instance
storage_service = StorageService()
