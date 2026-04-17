from uuid import UUID

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.interview import InterviewSession
from app.models.notification import Notification
from app.models.user import User
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    async def create(self, **kwargs) -> AuditLog:
        log = AuditLog(**kwargs)
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_logs(self, limit: int = 100) -> list[AuditLog]:
        result = await self.db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
        return list(result.scalars().all())


class AdminRepository(BaseRepository[User]):
    async def stats(self) -> dict[str, int]:
        users_total = await self.db.scalar(select(func.count(User.id)))
        candidates_total = await self.db.scalar(select(func.count(Candidate.id)))
        interviews_total = await self.db.scalar(select(func.count(InterviewSession.id)))
        pending_notifications_total = await self.db.scalar(
            select(func.count(Notification.id)).where(Notification.is_read.is_(False))
        )
        return {
            'users_total': int(users_total or 0),
            'candidates_total': int(candidates_total or 0),
            'interviews_total': int(interviews_total or 0),
            'pending_notifications_total': int(pending_notifications_total or 0),
        }

