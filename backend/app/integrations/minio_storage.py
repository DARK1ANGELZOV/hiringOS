import io
import mimetypes
from datetime import timedelta
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


class MinioStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket_documents
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, *, filename: str, data: bytes, content_type: str | None = None) -> tuple[str, str]:
        ext = filename.split('.')[-1].lower()
        object_key = f'{uuid4()}.{ext}'
        guessed = content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=guessed,
        )
        return self.bucket, object_key

    def get_file(self, object_key: str) -> bytes:
        response = self.client.get_object(self.bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presigned_download_url(self, *, object_key: str, expires_seconds: int) -> str:
        return self.client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=max(1, expires_seconds)),
        )

    def remove_file(self, *, object_key: str) -> None:
        self.client.remove_object(self.bucket, object_key)


def get_minio_storage() -> MinioStorage:
    storage = MinioStorage()
    try:
        storage.ensure_bucket()
    except S3Error:
        pass
    return storage

