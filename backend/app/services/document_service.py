from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.metrics import UPLOAD_EVENTS_TOTAL
from app.integrations.minio_storage import MinioStorage
from app.models.enums import DocumentType
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.document_repository import DocumentRepository
from app.services.file_security_service import FileSecurityService


class DocumentService:
    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        candidate_repository: CandidateRepository,
        storage: MinioStorage,
    ):
        self.document_repository = document_repository
        self.candidate_repository = candidate_repository
        self.storage = storage
        self.settings = get_settings()

    async def upload(
        self,
        *,
        candidate_id: UUID,
        file: UploadFile,
        uploaded_by_user_id: UUID | None,
        document_type: DocumentType,
    ):
        candidate = await self.candidate_repository.get_by_id(candidate_id)
        if not candidate:
            UPLOAD_EVENTS_TOTAL.labels(result='candidate_not_found').inc()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')

        content, detected_mime = await self._validate_upload(file=file)

        bucket, object_key = self.storage.upload_file(
            filename=file.filename,
            data=content,
            content_type=detected_mime,
        )
        document = await self.document_repository.create(
            candidate_id=candidate_id,
            uploaded_by_user_id=uploaded_by_user_id,
            bucket=bucket,
            object_key=object_key,
            original_filename=file.filename,
            content_type=detected_mime,
            size_bytes=len(content),
            document_type=document_type,
        )
        UPLOAD_EVENTS_TOTAL.labels(result='success').inc()
        return document, content

    async def list_for_candidate(self, candidate_id: UUID):
        return await self.document_repository.list_by_candidate(candidate_id)

    async def get(self, document_id: UUID):
        document = await self.document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found')
        return document

    async def create_download_url(self, *, document_id: UUID) -> tuple[str, int]:
        document = await self.get(document_id)
        expires_in = self.settings.signed_url_expire_seconds
        url = self.storage.presigned_download_url(object_key=document.object_key, expires_seconds=expires_in)
        return url, expires_in

    async def delete(self, *, document_id: UUID) -> None:
        document = await self.get(document_id)
        try:
            self.storage.remove_file(object_key=document.object_key)
        except Exception:
            # If object already missing in storage, still remove DB row.
            pass

        deleted = await self.document_repository.delete(document.id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found')

    async def replace(
        self,
        *,
        document_id: UUID,
        file: UploadFile,
        uploaded_by_user_id: UUID | None,
    ):
        document = await self.get(document_id)
        content, detected_mime = await self._validate_upload(file=file)

        bucket, object_key = self.storage.upload_file(
            filename=file.filename,
            data=content,
            content_type=detected_mime,
        )

        old_object_key = document.object_key
        updated = await self.document_repository.update(
            document,
            bucket=bucket,
            object_key=object_key,
            original_filename=file.filename,
            content_type=detected_mime,
            size_bytes=len(content),
            uploaded_by_user_id=uploaded_by_user_id,
        )

        try:
            self.storage.remove_file(object_key=old_object_key)
        except Exception:
            pass

        return updated

    async def _validate_upload(self, *, file: UploadFile) -> tuple[bytes, str]:
        if not file.filename:
            UPLOAD_EVENTS_TOTAL.labels(result='missing_filename').inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File name is required')

        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.settings.max_upload_size_mb:
            UPLOAD_EVENTS_TOTAL.labels(result='size_exceeded').inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File too large')

        _, detected_mime = FileSecurityService.validate_upload(
            filename=file.filename,
            content=content,
            provided_content_type=file.content_type,
            allowed_extensions=self.settings.allowed_extensions,
            allowed_mime_types=self.settings.allowed_mime_types,
        )

        safe, reason = FileSecurityService.malware_precheck(content)
        if not safe:
            if self.settings.malware_scan_block_on_detection:
                UPLOAD_EVENTS_TOTAL.labels(result='malware_blocked').inc()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason or 'Malware pre-check failed')
        if safe is False and reason is None and self.settings.malware_scan_block_on_error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Malware pre-check unavailable')

        return content, detected_mime
