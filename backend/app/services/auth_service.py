import hashlib
from uuid import uuid4
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import InviteAcceptRequest, LoginRequest, RegisterRequest, TokenPair
from app.services.organization_service import OrganizationService
from app.services.sanitizer import sanitize_text


class AuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        refresh_repository: RefreshTokenRepository,
        organization_repository: OrganizationRepository,
    ):
        self.user_repository = user_repository
        self.refresh_repository = refresh_repository
        self.organization_repository = organization_repository
        self.organization_service = OrganizationService(organization_repository)
        self.settings = get_settings()

    async def register(self, payload: RegisterRequest) -> TokenPair:
        existing = await self.user_repository.get_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')

        user = await self.user_repository.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=sanitize_text(payload.full_name) or payload.full_name,
            role=UserRole.CANDIDATE,
        )

        org_id: UUID | None = None
        active_role: UserRole = UserRole.CANDIDATE
        if await self.organization_service.bootstrap_available():
            bootstrap_org = await self.organization_service.create_bootstrap_for_user(
                user_id=user.id,
                user_full_name=user.full_name,
                user_email=user.email,
            )
            user.role = UserRole.ADMIN
            org_id = bootstrap_org.id
            active_role = UserRole.ADMIN
            await self.user_repository.db.flush()

        return await self._issue_tokens(
            user_id=user.id,
            role=active_role.value,
            org_id=str(org_id) if org_id else None,
            family_id=uuid4().hex,
            parent_jti=None,
            session_id=uuid4().hex,
        )

    async def login(self, payload: LoginRequest) -> TokenPair:
        user = await self.user_repository.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account blocked')

        membership = await self.organization_repository.get_default_membership_for_user(user_id=user.id)
        active_role = membership.role.value if membership else user.role.value
        org_id = str(membership.organization_id) if membership else None

        return await self._issue_tokens(
            user_id=user.id,
            role=active_role,
            org_id=org_id,
            family_id=uuid4().hex,
            parent_jti=None,
            session_id=uuid4().hex,
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get('sub')
        jti = payload.get('jti')
        family_id = payload.get('family_id')
        parent_session_id = payload.get('session_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
        if not jti or not family_id or not parent_session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')

        token_record = await self.refresh_repository.get_by_jti(jti)
        if not token_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token revoked')

        if token_record.token_hash != self._token_hash(refresh_token):
            await self.refresh_repository.mark_reuse_detected(token_record)
            await self.refresh_repository.revoke_family(token_record.family_id, reason='token_reuse_detected')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token reuse detected')

        if token_record.revoked_at is not None:
            await self.refresh_repository.mark_reuse_detected(token_record)
            await self.refresh_repository.revoke_family(token_record.family_id, reason='token_reuse_detected')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token revoked')

        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            await self.refresh_repository.revoke(token_record, reason='expired')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired')

        user = await self.user_repository.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            await self.refresh_repository.revoke_family(token_record.family_id, reason='user_inactive')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User unavailable')

        await self.refresh_repository.revoke(token_record, reason='rotated')
        return await self._issue_tokens(
            user_id=user.id,
            role=token_record.role or user.role.value,
            org_id=str(token_record.org_id) if token_record.org_id else None,
            family_id=token_record.family_id,
            parent_jti=token_record.jti,
            session_id=token_record.session_id,
        )

    async def logout(self, user_id: UUID) -> None:
        await self.refresh_repository.revoke_all_for_user(user_id)

    async def accept_invite(self, payload: InviteAcceptRequest) -> TokenPair:
        invite = await self.organization_service.validate_invite_acceptance(token=payload.token, email=payload.email)
        user = await self.user_repository.get_by_email(payload.email)

        if user:
            if not verify_password(payload.password, user.hashed_password):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account blocked')
        else:
            user = await self.user_repository.create(
                email=payload.email,
                hashed_password=hash_password(payload.password),
                full_name=sanitize_text(payload.full_name) or payload.full_name,
                role=invite.role,
            )

        membership = await self.organization_service.assign_membership_from_invite(invite=invite, user_id=user.id)

        if invite.role in {UserRole.ADMIN, UserRole.HR, UserRole.MANAGER}:
            user.role = invite.role
            await self.user_repository.db.flush()

        return await self._issue_tokens(
            user_id=user.id,
            role=membership.role.value,
            org_id=str(membership.organization_id),
            family_id=uuid4().hex,
            parent_jti=None,
            session_id=uuid4().hex,
        )

    async def change_password(self, *, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Current password is invalid')
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='New password must be different')

        user.hashed_password = hash_password(new_password)
        await self.user_repository.db.flush()
        await self.refresh_repository.revoke_all_for_user(user_id, reason='password_changed')

    @staticmethod
    def _token_hash(value: str) -> str:
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    async def _issue_tokens(
        self,
        *,
        user_id: UUID,
        role: str,
        org_id: str | None,
        family_id: str,
        parent_jti: str | None,
        session_id: str,
    ) -> TokenPair:
        access_jti = uuid4().hex
        refresh_jti = uuid4().hex
        access_token, access_expires = create_access_token(
            str(user_id),
            role,
            org_id=org_id,
            session_id=session_id,
            jti=access_jti,
        )
        refresh_token, refresh_expires = create_refresh_token(
            str(user_id),
            jti=refresh_jti,
            family_id=family_id,
            session_id=session_id,
            org_id=org_id,
            role=role,
            parent_jti=parent_jti,
        )
        await self.refresh_repository.create(
            user_id=user_id,
            token_hash=self._token_hash(refresh_token),
            expires_at=refresh_expires,
            jti=refresh_jti,
            family_id=family_id,
            parent_jti=parent_jti,
            session_id=session_id,
            org_id=UUID(org_id) if org_id else None,
            role=role,
        )

        return TokenPair(
            access_token=access_token,
            access_token_expires_at=access_expires,
            refresh_token=refresh_token,
            refresh_token_expires_at=refresh_expires,
        )

