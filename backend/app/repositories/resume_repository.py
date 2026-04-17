from uuid import UUID

from sqlalchemy import select

from app.models.resume import ResumeProfile
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[ResumeProfile]):
    async def upsert_for_candidate(self, *, candidate_id: UUID, defaults: dict) -> ResumeProfile:
        existing = await self.get_by_candidate(candidate_id)
        if existing:
            for key, value in defaults.items():
                setattr(existing, key, value)
            await self.db.flush()
            return existing

        profile = ResumeProfile(candidate_id=candidate_id, **defaults)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_by_candidate(self, candidate_id: UUID) -> ResumeProfile | None:
        result = await self.db.execute(select(ResumeProfile).where(ResumeProfile.candidate_id == candidate_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, resume_id: UUID) -> ResumeProfile | None:
        result = await self.db.execute(select(ResumeProfile).where(ResumeProfile.id == resume_id))
        return result.scalar_one_or_none()

