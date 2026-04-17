import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_use_cases, get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, InviteAcceptRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserMe
from app.schemas.common import MessageResponse
from app.use_cases.auth.use_cases import AuthUseCases

router = APIRouter(prefix='/auth', tags=['auth'])
settings = get_settings()


def _require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    csrf_header = request.headers.get('x-csrf-token')
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='CSRF validation failed')


def _set_auth_cookies(response: Response, tokens: TokenPair) -> None:
    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key=settings.access_cookie_name,
        value=tokens.access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path='/',
        expires=tokens.access_token_expires_at,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path='/',
        expires=tokens.refresh_token_expires_at,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path='/',
        expires=tokens.refresh_token_expires_at,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.access_cookie_name, path='/', domain=settings.auth_cookie_domain)
    response.delete_cookie(settings.refresh_cookie_name, path='/', domain=settings.auth_cookie_domain)
    response.delete_cookie(settings.csrf_cookie_name, path='/', domain=settings.auth_cookie_domain)


@router.post('/register', response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit('20/minute')
async def register(
    request: Request,
    response: Response,
    payload: RegisterRequest,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
):
    _ = request
    result = await use_cases.register(payload)
    _set_auth_cookies(response, result)
    await db.commit()
    return result


@router.post('/login', response_model=TokenPair)
@limiter.limit('30/minute')
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
):
    _ = request
    result = await use_cases.login(payload)
    _set_auth_cookies(response, result)
    await db.commit()
    return result


@router.post('/refresh', response_model=TokenPair)
@limiter.limit('40/minute')
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    refresh_token = payload.refresh_token or request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token missing')

    result = await use_cases.refresh(refresh_token)
    _set_auth_cookies(response, result)
    await db.commit()
    return result


@router.post('/logout', response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_csrf(request)
    await use_cases.logout(UUID(str(current_user.id)))
    _clear_auth_cookies(response)
    await db.commit()
    return MessageResponse(message='Logged out successfully')


@router.get('/me', response_model=UserMe)
async def me(current_user: User = Depends(get_current_user)):
    return UserMe(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=getattr(current_user, 'active_role', current_user.role).value,
        active_org_id=getattr(current_user, 'active_org_id', None),
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post('/invite/accept', response_model=TokenPair)
@limiter.limit('20/minute')
async def invite_accept(
    request: Request,
    response: Response,
    payload: InviteAcceptRequest,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
):
    _ = request
    result = await use_cases.accept_invite(payload)
    _set_auth_cookies(response, result)
    await db.commit()
    return result


@router.post('/change-password', response_model=MessageResponse)
@limiter.limit('20/minute')
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_csrf(request)
    await use_cases.change_password(
        user_id=UUID(str(current_user.id)),
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    await db.commit()
    return MessageResponse(message='Password updated')
