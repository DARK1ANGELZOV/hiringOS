from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.integrations.ai_service import ai_client
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.sanitizer import sanitize_payload


class CandidateService:
    ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
        'new': {'screening', 'reserve', 'rejected'},
        'screening': {'hr_interview', 'reserve', 'rejected'},
        'hr_interview': {'tech_interview', 'manager_review', 'reserve', 'rejected'},
        'tech_interview': {'manager_review', 'interview_done', 'reserve', 'rejected'},
        'manager_review': {'interview_done', 'reserve', 'rejected'},
        'interview_done': {'decision_pending', 'offer', 'reserve', 'rejected'},
        'decision_pending': {'offer', 'reserve', 'rejected'},
        'reserve': {'screening', 'offer', 'rejected'},
        'offer': {'hired', 'rejected', 'reserve'},
        'hired': set(),
        'rejected': set(),
    }

    def __init__(self, repository: CandidateRepository):
        self.repository = repository

    async def create(self, payload: CandidateCreate, created_by_user_id: UUID | None):
        data = sanitize_payload(payload.model_dump())
        self._normalize_profile_terms(data)
        candidate = await self.repository.create(**data, created_by_user_id=created_by_user_id)
        await self.repository.create_status_history(
            candidate_id=candidate.id,
            previous_status=None,
            new_status=candidate.status,
            changed_by_user_id=created_by_user_id,
            comment='Candidate profile created',
            metadata_json={'source': 'candidate_create'},
        )
        await self._refresh_embedding(candidate)
        return candidate

    async def get(self, candidate_id: UUID):
        candidate = await self.repository.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')
        return candidate

    async def get_by_owner(self, owner_user_id: UUID):
        candidate = await self.repository.get_by_owner_user_id(owner_user_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate profile not found')
        return candidate

    async def list(self, status: str | None, limit: int, offset: int, organization_id: UUID | None = None):
        return await self.repository.list(status=status, limit=limit, offset=offset, organization_id=organization_id)

    async def list_for_owner(self, owner_user_id: UUID, limit: int, offset: int):
        return await self.repository.list_for_owner(owner_user_id=owner_user_id, limit=limit, offset=offset)

    async def list_for_manager(self, *, manager_user_id: UUID, organization_id: UUID, status: str | None, limit: int, offset: int):
        return await self.repository.list_for_manager(
            manager_user_id=manager_user_id,
            organization_id=organization_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def update(self, candidate_id: UUID, payload: CandidateUpdate, changed_by_user_id: UUID | None = None):
        candidate = await self.get(candidate_id)
        data = sanitize_payload(payload.model_dump(exclude_unset=True))
        status_comment = data.pop('status_comment', None)
        requested_status = data.pop('status', None)
        if requested_status and requested_status != candidate.status:
            await self.change_status(
                candidate_id=candidate_id,
                new_status=requested_status,
                changed_by_user_id=changed_by_user_id,
                comment=status_comment,
                metadata_json={'source': 'candidate_update'},
            )
        self._normalize_profile_terms(data)
        candidate = await self.repository.update(candidate, **data)
        await self._refresh_embedding(candidate)
        return candidate

    async def change_status(
        self,
        *,
        candidate_id: UUID,
        new_status: str,
        changed_by_user_id: UUID | None,
        comment: str | None = None,
        metadata_json: dict | None = None,
    ):
        candidate = await self.get(candidate_id)
        normalized = self._normalize_status(new_status)
        previous_status = self._normalize_status(candidate.status)

        if normalized != previous_status:
            self._assert_status_transition(previous_status=previous_status, new_status=normalized)
            candidate.status = normalized
            await self.repository.create_status_history(
                candidate_id=candidate.id,
                previous_status=previous_status,
                new_status=normalized,
                changed_by_user_id=changed_by_user_id,
                comment=comment,
                metadata_json=metadata_json or {},
            )
            await self.repository.db.flush()
        return candidate

    async def list_status_history(self, *, candidate_id: UUID, limit: int = 200):
        await self.get(candidate_id)
        return await self.repository.list_status_history(candidate_id=candidate_id, limit=limit)

    async def search(self, *, query: str, limit: int):
        embedding = await ai_client.embedding(text=query)
        return await self.repository.search_by_embedding(embedding, limit)

    async def _refresh_embedding(self, candidate) -> None:
        embedding_source = self._candidate_embedding_text(candidate)
        if not embedding_source.strip():
            return
        try:
            embedding = await ai_client.embedding(text=embedding_source)
            candidate.embedding = embedding
            await self.repository.db.flush()
        except Exception:
            candidate.embedding = None
            await self.repository.db.flush()

    @staticmethod
    def _candidate_embedding_text(candidate) -> str:
        skills = ', '.join(item.get('name', '') for item in candidate.skills if isinstance(item, dict))
        experience = ' '.join(item.get('title', '') + ' ' + item.get('description', '') for item in candidate.experience if isinstance(item, dict))
        return ' '.join(
            filter(
                None,
                [
                    candidate.full_name,
                    candidate.headline or '',
                    candidate.summary or '',
                    candidate.skills_raw or '',
                    candidate.languages_raw or '',
                    skills,
                    experience,
                ],
            )
        )

    def _normalize_profile_terms(self, data: dict) -> None:
        skills_raw = data.get('skills_raw')
        if isinstance(skills_raw, str):
            parsed_skills = self._parse_terms_to_objects(skills_raw)
            if parsed_skills:
                data['skills'] = [{'name': value, 'level': None} for value in parsed_skills]

        languages_raw = data.get('languages_raw')
        if isinstance(languages_raw, str):
            parsed_languages = self._parse_terms_to_objects(languages_raw)
            if parsed_languages:
                data['languages'] = [{'name': value, 'level': None} for value in parsed_languages]

    @staticmethod
    def _parse_terms_to_objects(value: str) -> list[str]:
        delimiters = ['\n', ',', ';', '|']
        normalized = value
        for delimiter in delimiters[1:]:
            normalized = normalized.replace(delimiter, delimiters[0])
        rows = [item.strip() for item in normalized.split(delimiters[0])]
        rows = [item for item in rows if item]
        unique: list[str] = []
        seen: set[str] = set()
        for row in rows:
            key = row.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique[:200]

    def _assert_status_transition(self, *, previous_status: str, new_status: str) -> None:
        allowed = self.ALLOWED_STATUS_TRANSITIONS.get(previous_status)
        if allowed is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Unknown candidate status: {previous_status}')
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Invalid candidate status transition: {previous_status} -> {new_status}',
            )

    @staticmethod
    def _normalize_status(value: str) -> str:
        return value.strip().lower()

