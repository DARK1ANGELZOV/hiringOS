from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy import func, select

from app.models.candidate import Candidate, CandidateStatusHistory
from app.models.organization import ManagerCandidateAccess
from app.repositories.base import BaseRepository


class CandidateRepository(BaseRepository[Candidate]):
    async def create(self, **kwargs) -> Candidate:
        candidate = Candidate(**kwargs)
        self.db.add(candidate)
        await self.db.flush()
        return candidate

    async def get_by_id(self, candidate_id: UUID) -> Candidate | None:
        result = await self.db.execute(select(Candidate).where(Candidate.id == candidate_id))
        return result.scalar_one_or_none()

    async def get_by_owner_user_id(self, owner_user_id: UUID) -> Candidate | None:
        result = await self.db.execute(select(Candidate).where(Candidate.owner_user_id == owner_user_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
        organization_id: UUID | None = None,
    ) -> tuple[list[Candidate], int]:
        query = select(Candidate)
        count_query = select(func.count(Candidate.id))
        if organization_id is not None:
            query = query.where(Candidate.organization_id == organization_id)
            count_query = count_query.where(Candidate.organization_id == organization_id)
        if status:
            query = query.where(Candidate.status == status)
            count_query = count_query.where(Candidate.status == status)

        query = query.order_by(Candidate.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        rows = result.scalars().all()
        total = await self.db.scalar(count_query)
        return list(rows), int(total or 0)

    async def list_for_manager(
        self,
        *,
        manager_user_id: UUID,
        organization_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Candidate], int]:
        query = (
            select(Candidate)
            .join(ManagerCandidateAccess, ManagerCandidateAccess.candidate_id == Candidate.id)
            .where(
                ManagerCandidateAccess.manager_user_id == manager_user_id,
                ManagerCandidateAccess.organization_id == organization_id,
                ManagerCandidateAccess.is_active.is_(True),
            )
        )
        count_query = (
            select(func.count(Candidate.id))
            .join(ManagerCandidateAccess, ManagerCandidateAccess.candidate_id == Candidate.id)
            .where(
                ManagerCandidateAccess.manager_user_id == manager_user_id,
                ManagerCandidateAccess.organization_id == organization_id,
                ManagerCandidateAccess.is_active.is_(True),
            )
        )
        if status:
            query = query.where(Candidate.status == status)
            count_query = count_query.where(Candidate.status == status)

        result = await self.db.execute(query.order_by(Candidate.created_at.desc()).limit(limit).offset(offset))
        rows = result.scalars().all()
        total = await self.db.scalar(count_query)
        return list(rows), int(total or 0)

    async def manager_has_access(self, *, manager_user_id: UUID, organization_id: UUID, candidate_id: UUID) -> bool:
        value = await self.db.scalar(
            select(func.count(ManagerCandidateAccess.id)).where(
                ManagerCandidateAccess.manager_user_id == manager_user_id,
                ManagerCandidateAccess.organization_id == organization_id,
                ManagerCandidateAccess.candidate_id == candidate_id,
                ManagerCandidateAccess.is_active.is_(True),
            )
        )
        return int(value or 0) > 0

    async def list_for_owner(self, *, owner_user_id: UUID, limit: int = 100, offset: int = 0) -> tuple[list[Candidate], int]:
        query = (
            select(Candidate)
            .where(Candidate.owner_user_id == owner_user_id)
            .order_by(Candidate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count(Candidate.id)).where(Candidate.owner_user_id == owner_user_id)
        result = await self.db.execute(query)
        rows = result.scalars().all()
        total = await self.db.scalar(count_query)
        return list(rows), int(total or 0)

    async def update(self, candidate: Candidate, **kwargs) -> Candidate:
        for field, value in kwargs.items():
            if value is not None:
                setattr(candidate, field, value)
        await self.db.flush()
        return candidate

    async def create_status_history(self, **kwargs) -> CandidateStatusHistory:
        row = CandidateStatusHistory(**kwargs)
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_status_history(self, *, candidate_id: UUID, limit: int = 200) -> list[CandidateStatusHistory]:
        result = await self.db.execute(
            select(CandidateStatusHistory)
            .where(CandidateStatusHistory.candidate_id == candidate_id)
            .order_by(CandidateStatusHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_embedding(self, embedding: list[float], limit: int = 20) -> list[tuple[Candidate, float]]:
        result = await self.db.execute(select(Candidate).where(Candidate.embedding.is_not(None)))
        rows = list(result.scalars().all())

        scored: list[tuple[Candidate, float]] = []
        for row in rows:
            candidate_embedding = row.embedding or []
            score = self._cosine_similarity(embedding, candidate_embedding)
            if score is None:
                continue
            scored.append((row, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(1, limit)]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
        if not left or not right:
            return None
        if len(left) != len(right):
            return None

        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return None
        return float(dot / (left_norm * right_norm))

