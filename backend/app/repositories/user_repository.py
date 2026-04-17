from uuid import UUID

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str, full_name: str, role: str) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def list_users(self, *, limit: int = 200, offset: int = 0) -> list[User]:
        result = await self.db.execute(select(User).order_by(User.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def set_active(self, *, user_id: UUID, is_active: bool) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = is_active
        await self.db.flush()
        return user

    async def set_role(self, *, user_id: UUID, role: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.role = role
        await self.db.flush()
        return user

