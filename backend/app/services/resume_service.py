from uuid import UUID

from app.integrations.ai_service import ai_client
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.resume_repository import ResumeRepository


class ResumeService:
    def __init__(
        self,
        *,
        resume_repository: ResumeRepository,
        candidate_repository: CandidateRepository,
    ):
        self.resume_repository = resume_repository
        self.candidate_repository = candidate_repository

    async def parse_and_store(
        self,
        *,
        candidate_id: UUID,
        document_id: UUID,
        filename: str,
        file_content: bytes,
    ):
        fallback_used = False
        parser_status = 'success'
        parser_error = None
        structured_data: dict = {}
        raw_text: str | None = None

        try:
            ai_result = await ai_client.parse_resume(file_name=filename, file_content=file_content)
            structured_data = ai_result.get('structured', {})
            parser_status = ai_result.get('status', 'success')
            fallback_used = bool(ai_result.get('fallback_used', False))
            parser_error = ai_result.get('error')
            raw_text = ai_result.get('raw_text')
        except Exception as exc:
            parser_status = 'failed'
            fallback_used = True
            parser_error = str(exc)
            structured_data = {}

        profile = await self.resume_repository.upsert_for_candidate(
            candidate_id=candidate_id,
            defaults={
                'document_id': document_id,
                'parser_status': parser_status,
                'parser_error': parser_error,
                'structured_data': structured_data,
                'raw_text': raw_text,
            },
        )

        candidate = await self.candidate_repository.get_by_id(candidate_id)
        if candidate:
            self._apply_structured_to_candidate(candidate=candidate, structured_data=structured_data)
            await self.resume_repository.db.flush()

        return profile, fallback_used

    async def parse_text_and_store(self, *, candidate_id: UUID, text: str):
        fallback_used = False
        parser_status = 'success'
        parser_error = None
        structured_data: dict = {}
        raw_text: str | None = text

        try:
            ai_result = await ai_client.parse_resume_text(text=text)
            structured_data = ai_result.get('structured', {})
            parser_status = ai_result.get('status', 'success')
            fallback_used = bool(ai_result.get('fallback_used', False))
            parser_error = ai_result.get('error')
            raw_text = ai_result.get('raw_text') or raw_text
        except Exception as exc:
            parser_status = 'failed'
            fallback_used = True
            parser_error = str(exc)
            structured_data = {}

        profile = await self.resume_repository.upsert_for_candidate(
            candidate_id=candidate_id,
            defaults={
                'document_id': None,
                'parser_status': parser_status,
                'parser_error': parser_error,
                'structured_data': structured_data,
                'raw_text': raw_text,
            },
        )

        candidate = await self.candidate_repository.get_by_id(candidate_id)
        if candidate:
            self._apply_structured_to_candidate(candidate=candidate, structured_data=structured_data)
            await self.resume_repository.db.flush()

        return profile, fallback_used

    async def get_candidate_resume(self, candidate_id: UUID):
        return await self.resume_repository.get_by_candidate(candidate_id)

    async def update_manual(self, resume_id: UUID, structured_data: dict):
        profile = await self.resume_repository.get_by_id(resume_id)
        if not profile:
            return None
        profile.structured_data = structured_data
        profile.parser_status = 'manual'
        await self.resume_repository.db.flush()
        return profile

    @staticmethod
    def _apply_structured_to_candidate(*, candidate, structured_data: dict) -> None:
        if not structured_data:
            return
        candidate.full_name = structured_data.get('full_name') or candidate.full_name
        contacts = structured_data.get('contacts') or {}
        candidate.email = contacts.get('email') or candidate.email
        candidate.phone = contacts.get('phone') or candidate.phone
        candidate.skills = structured_data.get('skills') or candidate.skills
        candidate.experience = structured_data.get('experience') or candidate.experience
        candidate.education = structured_data.get('education') or candidate.education
        candidate.projects = structured_data.get('projects') or candidate.projects
        candidate.languages = structured_data.get('languages') or candidate.languages

