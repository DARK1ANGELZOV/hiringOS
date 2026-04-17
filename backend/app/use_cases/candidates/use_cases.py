from uuid import UUID

from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService
from app.services.notification_service import NotificationService


class CandidateUseCases:
    def __init__(
        self,
        *,
        candidate_service: CandidateService,
        audit_service: AuditService,
        notification_service: NotificationService,
    ):
        self.candidate_service = candidate_service
        self.audit_service = audit_service
        self.notification_service = notification_service

    async def create(self, payload: CandidateCreate, actor_user_id: UUID | None):
        candidate = await self.candidate_service.create(payload, created_by_user_id=actor_user_id)
        if candidate.owner_user_id:
            await self.notification_service.create(
                user_id=candidate.owner_user_id,
                title='Профиль кандидата создан',
                message='Ваш профиль в ATS был создан HR-командой.',
                entity_type='candidate',
                entity_id=str(candidate.id),
            )
        await self.audit_service.log(
            action='candidate.create',
            user_id=actor_user_id,
            entity_type='candidate',
            entity_id=str(candidate.id),
        )
        return candidate

    async def update(self, candidate_id: UUID, payload: CandidateUpdate, actor_user_id: UUID | None):
        candidate = await self.candidate_service.update(candidate_id, payload, changed_by_user_id=actor_user_id)
        if candidate.owner_user_id:
            await self.notification_service.create(
                user_id=candidate.owner_user_id,
                title='Профиль кандидата обновлен',
                message='Данные вашего профиля были обновлены.',
                entity_type='candidate',
                entity_id=str(candidate.id),
            )
        await self.audit_service.log(
            action='candidate.update',
            user_id=actor_user_id,
            entity_type='candidate',
            entity_id=str(candidate.id),
        )
        return candidate

    async def change_status(
        self,
        *,
        candidate_id: UUID,
        new_status: str,
        actor_user_id: UUID | None,
        comment: str | None = None,
        metadata_json: dict | None = None,
    ):
        candidate = await self.candidate_service.change_status(
            candidate_id=candidate_id,
            new_status=new_status,
            changed_by_user_id=actor_user_id,
            comment=comment,
            metadata_json=metadata_json,
        )
        if candidate.owner_user_id:
            await self.notification_service.create(
                user_id=candidate.owner_user_id,
                title='Статус кандидата изменен',
                message=f'Ваш статус в процессе подбора: {candidate.status}.',
                entity_type='candidate',
                entity_id=str(candidate.id),
            )
        await self.audit_service.log(
            action='candidate.status.change',
            user_id=actor_user_id,
            entity_type='candidate',
            entity_id=str(candidate.id),
            metadata_json={'new_status': candidate.status, 'comment': comment},
        )
        return candidate

    async def status_history(self, *, candidate_id: UUID, limit: int = 200):
        return await self.candidate_service.list_status_history(candidate_id=candidate_id, limit=limit)

    async def get(self, candidate_id: UUID):
        return await self.candidate_service.get(candidate_id)

    async def get_by_owner(self, owner_user_id: UUID):
        return await self.candidate_service.get_by_owner(owner_user_id)

    async def list(
        self,
        status: str | None,
        limit: int,
        offset: int,
        owner_user_id: UUID | None = None,
        organization_id: UUID | None = None,
        manager_user_id: UUID | None = None,
    ):
        if owner_user_id:
            return await self.candidate_service.list_for_owner(owner_user_id=owner_user_id, limit=limit, offset=offset)
        if manager_user_id and organization_id:
            return await self.candidate_service.list_for_manager(
                manager_user_id=manager_user_id,
                organization_id=organization_id,
                status=status,
                limit=limit,
                offset=offset,
            )
        return await self.candidate_service.list(status=status, limit=limit, offset=offset, organization_id=organization_id)

    async def search(self, query: str, limit: int):
        return await self.candidate_service.search(query=query, limit=limit)
