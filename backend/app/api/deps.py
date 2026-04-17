from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.integrations.minio_storage import get_minio_storage
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit_repository import AdminRepository, AuditRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.test_repository import KnowledgeTestRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vacancy_repository import VacancyRepository
from app.services.admin_service import AdminService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.candidate_service import CandidateService
from app.services.document_service import DocumentService
from app.services.feedback_service import FeedbackService
from app.services.interview_service import InterviewService
from app.services.notification_service import NotificationService
from app.services.resume_service import ResumeService
from app.services.test_service import KnowledgeTestService
from app.use_cases.admin.use_cases import AdminUseCases
from app.use_cases.auth.use_cases import AuthUseCases
from app.use_cases.candidates.use_cases import CandidateUseCases
from app.use_cases.interviews.use_cases import InterviewUseCases
from app.use_cases.notifications.use_cases import NotificationUseCases
from app.use_cases.resumes.use_cases import ResumeUseCases

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')
oauth2_optional_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login', auto_error=False)
settings = get_settings()


@dataclass
class AuthContext:
    user: User
    active_role: UserRole
    active_org_id: UUID | None
    session_id: str | None
    token_jti: str | None


def _resolve_role(role_raw: str | None, fallback: UserRole) -> UserRole:
    if not role_raw:
        return fallback
    try:
        return UserRole(role_raw)
    except ValueError:
        return fallback


async def _build_auth_context(db: AsyncSession, payload: dict) -> AuthContext:
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication')

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User unavailable')

    active_role = _resolve_role(payload.get('role'), user.role)
    active_org_id_raw = payload.get('org_id')
    active_org_id = UUID(active_org_id_raw) if active_org_id_raw else None

    if active_org_id is not None:
        organization_repo = OrganizationRepository(db)
        membership = await organization_repo.get_membership(
            organization_id=active_org_id,
            user_id=user.id,
            role=active_role,
        )
        if not membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')

    setattr(user, 'active_role', active_role)
    setattr(user, 'active_org_id', active_org_id)
    setattr(user, 'session_id', payload.get('session_id'))
    setattr(user, 'token_jti', payload.get('jti'))

    return AuthContext(
        user=user,
        active_role=active_role,
        active_org_id=active_org_id,
        session_id=payload.get('session_id'),
        token_jti=payload.get('jti'),
    )


def _access_token_from_request(request: Request, oauth_token: str | None) -> str | None:
    if oauth_token:
        return oauth_token
    cookie_token = request.cookies.get(settings.access_cookie_name)
    if cookie_token:
        return cookie_token
    return None


async def get_auth_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_optional_scheme),
) -> AuthContext:
    resolved_token = _access_token_from_request(request, token)
    if not resolved_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    try:
        payload = decode_access_token(resolved_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication') from exc
    return await _build_auth_context(db, payload)


async def get_current_user(auth_context: AuthContext = Depends(get_auth_context)) -> User:
    return auth_context.user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_optional_scheme),
) -> User | None:
    resolved_token = _access_token_from_request(request, token)
    if not resolved_token:
        return None
    try:
        payload = decode_access_token(resolved_token)
        return (await _build_auth_context(db, payload)).user
    except Exception:
        return None


def require_roles(*roles: UserRole) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        active_role = getattr(user, 'active_role', user.role)
        if active_role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
        return user

    return checker


def get_auth_use_cases(db: AsyncSession = Depends(get_db)) -> AuthUseCases:
    return AuthUseCases(
        auth_service=AuthService(
            user_repository=UserRepository(db),
            refresh_repository=RefreshTokenRepository(db),
            organization_repository=OrganizationRepository(db),
        ),
        audit_service=AuditService(AuditRepository(db)),
    )


def get_candidate_use_cases(db: AsyncSession = Depends(get_db)) -> CandidateUseCases:
    return CandidateUseCases(
        candidate_service=CandidateService(CandidateRepository(db)),
        audit_service=AuditService(AuditRepository(db)),
        notification_service=NotificationService(NotificationRepository(db)),
    )


def get_resume_use_cases(db: AsyncSession = Depends(get_db)) -> ResumeUseCases:
    return ResumeUseCases(
        document_service=DocumentService(
            document_repository=DocumentRepository(db),
            candidate_repository=CandidateRepository(db),
            storage=get_minio_storage(),
        ),
        resume_service=ResumeService(
            resume_repository=ResumeRepository(db),
            candidate_repository=CandidateRepository(db),
        ),
        audit_service=AuditService(AuditRepository(db)),
    )


def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(
        document_repository=DocumentRepository(db),
        candidate_repository=CandidateRepository(db),
        storage=get_minio_storage(),
    )


def get_interview_use_cases(db: AsyncSession = Depends(get_db)) -> InterviewUseCases:
    interview_repository = InterviewRepository(db)
    return InterviewUseCases(
        interview_service=InterviewService(
            repository=interview_repository,
            candidate_repository=CandidateRepository(db),
            vacancy_repository=VacancyRepository(db),
            storage=get_minio_storage(),
        ),
        audit_service=AuditService(AuditRepository(db)),
        notification_service=NotificationService(NotificationRepository(db)),
    )


def get_feedback_service(db: AsyncSession = Depends(get_db)) -> FeedbackService:
    return FeedbackService(
        repository=FeedbackRepository(db),
        interview_repository=InterviewRepository(db),
    )


def get_notification_use_cases(db: AsyncSession = Depends(get_db)) -> NotificationUseCases:
    return NotificationUseCases(notification_service=NotificationService(NotificationRepository(db)))


def get_test_service(db: AsyncSession = Depends(get_db)) -> KnowledgeTestService:
    return KnowledgeTestService(
        repository=KnowledgeTestRepository(db),
        interview_repository=InterviewRepository(db),
        candidate_repository=CandidateRepository(db),
    )


def get_admin_use_cases(db: AsyncSession = Depends(get_db)) -> AdminUseCases:
    return AdminUseCases(
        admin_service=AdminService(
            admin_repository=AdminRepository(db),
            audit_repository=AuditRepository(db),
            user_repository=UserRepository(db),
            organization_repository=OrganizationRepository(db),
            refresh_repository=RefreshTokenRepository(db),
        )
    )
