from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'HiringOS API'
    app_env: str = 'development'
    app_debug: bool = False
    api_prefix: str = '/api/v1'

    database_url: str = 'postgresql+asyncpg://hiringos:hiringos@postgres:5432/hiringos'
    redis_url: str = 'redis://redis:6379/0'
    celery_broker_url: str = 'redis://redis:6379/0'
    celery_result_backend: str = 'redis://redis:6379/1'

    jwt_secret_key: str = 'replace_me'
    jwt_refresh_secret_key: str = 'replace_me_refresh'
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 14
    jwt_algorithm: str = 'HS256'
    jwt_issuer: str = 'hiringos-backend'
    jwt_audience: str = 'hiringos-clients'
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = 'lax'
    auth_cookie_domain: str | None = None
    access_cookie_name: str = 'hiringos_access'
    refresh_cookie_name: str = 'hiringos_refresh'
    csrf_cookie_name: str = 'hiringos_csrf'

    cors_origins: str = 'http://localhost:3000'

    minio_endpoint: str = 'minio:9000'
    minio_access_key: str = 'minioadmin'
    minio_secret_key: str = 'minioadmin'
    minio_secure: bool = False
    minio_bucket_documents: str = 'documents'

    ai_service_url: str = 'http://ai-service:8001'

    max_upload_size_mb: int = 10
    allowed_upload_extensions: str = '.pdf,.doc,.docx,.jpg,.jpeg,.png'
    allowed_upload_mime_types: str = (
        'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,'
        'image/jpeg,image/png'
    )
    signed_url_expire_seconds: int = 900
    malware_scan_block_on_detection: bool = True
    malware_scan_block_on_error: bool = False

    interview_queue_name: str = 'interviews'
    celery_default_queue: str = 'interviews'

    admin_bootstrap_token: str = ''
    invite_expires_hours: int = 72
    bootstrap_organization_name: str = 'HiringOS'

    @field_validator('cors_origins', mode='before')
    @classmethod
    def normalize_origins(cls, value: str) -> str:
        return value or ''

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_upload_extensions.split(',') if ext.strip()}

    @property
    def allowed_mime_types(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_upload_mime_types.split(',') if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

