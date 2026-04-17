from uuid import UUID

from sqlalchemy import select

from app.models.vacancy import Vacancy
from app.repositories.base import BaseRepository


class VacancyRepository(BaseRepository[Vacancy]):
    async def get_by_id(self, vacancy_id: UUID) -> Vacancy | None:
        result = await self.db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
        return result.scalar_one_or_none()

    async def create(self, **payload) -> Vacancy:
        vacancy = Vacancy(**payload)
        self.db.add(vacancy)
        await self.db.flush()
        return vacancy

    async def list(self, limit: int = 100) -> list[Vacancy]:
        result = await self.db.execute(select(Vacancy).order_by(Vacancy.created_at.desc()).limit(limit))
        return list(result.scalars().all())
