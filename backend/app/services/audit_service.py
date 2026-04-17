from uuid import UUID

from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def log(
        self,
        *,
        action: str,
        user_id: UUID | None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata_json: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        return await self.repository.create(
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_json or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

