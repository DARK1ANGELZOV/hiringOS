from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        jti: str,
        family_id: str,
        parent_jti: str | None,
        session_id: str,
        org_id: UUID | None,
        role: str | None,
    ) -> RefreshToken:
        refresh = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            jti=jti,
            family_id=family_id,
            parent_jti=parent_jti,
            session_id=session_id,
            org_id=org_id,
            role=role,
        )
        self.db.add(refresh)
        await self.db.flush()
        return refresh

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken, reason: str = 'logout') -> None:
        refresh_token.revoked_at = datetime.utcnow()
        refresh_token.revoked_reason = reason
        await self.db.flush()

    async def revoke_family(self, family_id: str, reason: str) -> None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.family_id == family_id))
        rows = result.scalars().all()
        now = datetime.utcnow()
        for row in rows:
            if row.revoked_at is None:
                row.revoked_at = now
            row.revoked_reason = reason
        await self.db.flush()

    async def mark_reuse_detected(self, refresh_token: RefreshToken) -> None:
        refresh_token.reuse_detected_at = datetime.utcnow()
        if refresh_token.revoked_at is None:
            refresh_token.revoked_at = datetime.utcnow()
        refresh_token.revoked_reason = 'reuse_detected'
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: UUID, reason: str = 'logout_all') -> None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
        rows = result.scalars().all()
        now = datetime.utcnow()
        for row in rows:
            row.revoked_at = now
            row.revoked_reason = reason
        await self.db.flush()

    async def list_user_sessions(self, *, user_id: UUID, limit: int = 200) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .order_by(RefreshToken.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

