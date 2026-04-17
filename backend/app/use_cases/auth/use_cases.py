from uuid import UUID

from app.schemas.auth import InviteAcceptRequest, LoginRequest, RegisterRequest
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


class AuthUseCases:
    def __init__(self, *, auth_service: AuthService, audit_service: AuditService):
        self.auth_service = auth_service
        self.audit_service = audit_service

    async def register(self, payload: RegisterRequest):
        tokens = await self.auth_service.register(payload)
        await self.audit_service.log(action='auth.register', user_id=None, metadata_json={'email': payload.email})
        return tokens

    async def login(self, payload: LoginRequest):
        tokens = await self.auth_service.login(payload)
        await self.audit_service.log(action='auth.login', user_id=None, metadata_json={'email': payload.email})
        return tokens

    async def refresh(self, refresh_token: str):
        tokens = await self.auth_service.refresh(refresh_token)
        await self.audit_service.log(action='auth.refresh', user_id=None)
        return tokens

    async def logout(self, user_id: UUID):
        await self.auth_service.logout(user_id)
        await self.audit_service.log(action='auth.logout', user_id=user_id)

    async def accept_invite(self, payload: InviteAcceptRequest):
        tokens = await self.auth_service.accept_invite(payload)
        await self.audit_service.log(action='auth.invite.accept', user_id=None, metadata_json={'email': payload.email})
        return tokens

    async def change_password(self, *, user_id: UUID, current_password: str, new_password: str):
        await self.auth_service.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
        )
        await self.audit_service.log(action='auth.change_password', user_id=user_id)

