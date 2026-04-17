from uuid import UUID

from fastapi import UploadFile

from app.models.enums import DocumentType
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService
from app.services.resume_service import ResumeService


class ResumeUseCases:
    def __init__(
        self,
        *,
        document_service: DocumentService,
        resume_service: ResumeService,
        audit_service: AuditService,
    ):
        self.document_service = document_service
        self.resume_service = resume_service
        self.audit_service = audit_service

    async def upload_and_parse(self, *, candidate_id: UUID, file: UploadFile, actor_user_id: UUID | None):
        document, content = await self.document_service.upload(
            candidate_id=candidate_id,
            file=file,
            uploaded_by_user_id=actor_user_id,
            document_type=DocumentType.RESUME,
        )
        profile, fallback_used = await self.resume_service.parse_and_store(
            candidate_id=candidate_id,
            document_id=document.id,
            filename=file.filename or 'resume.pdf',
            file_content=content,
        )
        await self.audit_service.log(
            action='resume.upload_and_parse',
            user_id=actor_user_id,
            entity_type='candidate',
            entity_id=str(candidate_id),
            metadata_json={'document_id': str(document.id), 'fallback_used': fallback_used},
        )
        return document, profile, fallback_used

    async def get_profile(self, candidate_id: UUID):
        return await self.resume_service.get_candidate_resume(candidate_id)

    async def parse_text(self, *, candidate_id: UUID, text: str, actor_user_id: UUID | None):
        profile, fallback_used = await self.resume_service.parse_text_and_store(
            candidate_id=candidate_id,
            text=text,
        )
        await self.audit_service.log(
            action='resume.parse_text',
            user_id=actor_user_id,
            entity_type='candidate',
            entity_id=str(candidate_id),
            metadata_json={'fallback_used': fallback_used},
        )
        return profile, fallback_used

    async def manual_update(self, resume_id: UUID, structured_data: dict, actor_user_id: UUID | None):
        profile = await self.resume_service.update_manual(resume_id, structured_data)
        if profile:
            await self.audit_service.log(
                action='resume.manual_update',
                user_id=actor_user_id,
                entity_type='resume_profile',
                entity_id=str(profile.id),
            )
        return profile

