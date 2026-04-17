from uuid import UUID

from sqlalchemy import select

from app.models.enums import VacancyApplicationStatus
from app.models.vacancy_application import VacancyApplication
from app.repositories.base import BaseRepository


class VacancyApplicationRepository(BaseRepository[VacancyApplication]):
    async def create(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        created_by_user_id: UUID | None,
        cover_letter_text: str | None,
        note: str | None,
        metadata_json: dict | None,
    ) -> VacancyApplication:
        item = VacancyApplication(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            created_by_user_id=created_by_user_id,
            cover_letter_text=cover_letter_text,
            note=note,
            metadata_json=metadata_json or {},
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_by_id(self, application_id: UUID) -> VacancyApplication | None:
        result = await self.db.execute(select(VacancyApplication).where(VacancyApplication.id == application_id))
        return result.scalar_one_or_none()

    async def get_by_vacancy_and_candidate(self, *, vacancy_id: UUID, candidate_id: UUID) -> VacancyApplication | None:
        result = await self.db.execute(
            select(VacancyApplication).where(
                VacancyApplication.vacancy_id == vacancy_id,
                VacancyApplication.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        vacancy_id: UUID | None = None,
        candidate_id: UUID | None = None,
        status: VacancyApplicationStatus | None = None,
        limit: int = 200,
    ) -> list[VacancyApplication]:
        query = select(VacancyApplication)
        if vacancy_id is not None:
            query = query.where(VacancyApplication.vacancy_id == vacancy_id)
        if candidate_id is not None:
            query = query.where(VacancyApplication.candidate_id == candidate_id)
        if status is not None:
            query = query.where(VacancyApplication.status == status)
        result = await self.db.execute(query.order_by(VacancyApplication.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def update_status(
        self,
        *,
        item: VacancyApplication,
        status: VacancyApplicationStatus,
        note: str | None = None,
    ) -> VacancyApplication:
        item.status = status
        if note is not None:
            item.note = note
        await self.db.flush()
        return item
