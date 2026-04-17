from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_use_cases, require_roles
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import AdminUserResponse, UserBlockRequest
from app.use_cases.admin.use_cases import AdminUseCases

router = APIRouter(prefix='/users', tags=['users'])


@router.patch('/{user_id}/block', response_model=AdminUserResponse)
async def block_user(
    user_id: UUID,
    payload: UserBlockRequest,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    user = await use_cases.block_user(user_id=user_id, reason=payload.reason)
    await db.commit()
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch('/{user_id}/unblock', response_model=AdminUserResponse)
async def unblock_user(
    user_id: UUID,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    user = await use_cases.unblock_user(user_id=user_id)
    await db.commit()
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
