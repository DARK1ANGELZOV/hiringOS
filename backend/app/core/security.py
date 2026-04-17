from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    *,
    org_id: str | None = None,
    session_id: str,
    jti: str,
) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expires_minutes)
    now = datetime.now(timezone.utc)
    payload = {
        'sub': subject,
        'org_id': org_id,
        'role': role,
        'session_id': session_id,
        'jti': jti,
        'token_type': 'access',
        'iat': now,
        'exp': expires_at,
        'iss': settings.jwt_issuer,
        'aud': settings.jwt_audience,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def create_refresh_token(
    subject: str,
    *,
    jti: str,
    family_id: str,
    session_id: str,
    org_id: str | None,
    role: str | None,
    parent_jti: str | None = None,
) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expires_days)
    now = datetime.now(timezone.utc)
    payload = {
        'sub': subject,
        'jti': jti,
        'family_id': family_id,
        'session_id': session_id,
        'org_id': org_id,
        'role': role,
        'parent_jti': parent_jti,
        'token_type': 'refresh',
        'iat': now,
        'exp': expires_at,
        'iss': settings.jwt_issuer,
        'aud': settings.jwt_audience,
    }
    token = jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
        if payload.get('token_type') != 'access':
            raise ValueError('Invalid token type')
        return payload
    except JWTError as exc:
        raise ValueError('Invalid access token') from exc


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_refresh_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
        if payload.get('token_type') != 'refresh':
            raise ValueError('Invalid token type')
        return payload
    except JWTError as exc:
        raise ValueError('Invalid refresh token') from exc

