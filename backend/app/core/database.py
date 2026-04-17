import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
import app.models  # noqa: F401
from app.models.base import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    except Exception as exc:
        message = str(exc).lower()
        vector_unavailable = (
            'extension "vector" is not available' in message
            or "extension 'vector' is not available" in message
            or 'could not open extension control file' in message
            or 'feature not supported' in message
        )
        if vector_unavailable:
            logger.warning('pgvector extension is unavailable, continuing without vector index support: %s', exc)
        else:
            raise

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_runtime_migrations(conn)


async def _apply_runtime_migrations(conn) -> None:
    # Keep schema compatible for existing dev volumes without destructive resets.
    statements = [
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS jti VARCHAR(64)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS family_id VARCHAR(64)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS parent_jti VARCHAR(64)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS session_id VARCHAR(64)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS org_id UUID",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS role VARCHAR(32)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS revoked_reason VARCHAR(128)",
        "ALTER TABLE IF EXISTS refresh_tokens ADD COLUMN IF NOT EXISTS reuse_detected_at TIMESTAMPTZ",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_jti ON refresh_tokens (jti)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family_id ON refresh_tokens (family_id)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_session_id ON refresh_tokens (session_id)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS organization_id UUID",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS date_of_birth DATE",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS city VARCHAR(255)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS skills_raw VARCHAR(8000)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS embedding JSONB",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'candidates'
                  AND column_name = 'embedding'
                  AND udt_name <> 'jsonb'
            ) THEN
                ALTER TABLE candidates ALTER COLUMN embedding TYPE JSONB USING NULL;
            END IF;
        END
        $$;
        """,
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS citizenship VARCHAR(255)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS github_url VARCHAR(500)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS portfolio_url VARCHAR(500)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS desired_position VARCHAR(255)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS specialization VARCHAR(255)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS level VARCHAR(64)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS salary_expectation VARCHAR(255)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS employment_type VARCHAR(128)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS work_format VARCHAR(128)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS work_schedule VARCHAR(128)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS relocation_ready BOOLEAN",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS travel_ready BOOLEAN",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS competencies_raw VARCHAR(8000)",
        "ALTER TABLE IF EXISTS candidates ADD COLUMN IF NOT EXISTS languages_raw VARCHAR(4000)",
        """
        CREATE TABLE IF NOT EXISTS candidate_status_history (
            id UUID PRIMARY KEY,
            candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            previous_status VARCHAR(64),
            new_status VARCHAR(64) NOT NULL,
            changed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            comment VARCHAR(2000),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_candidate_status_history_candidate_id ON candidate_status_history (candidate_id)",
        "CREATE INDEX IF NOT EXISTS ix_candidate_status_history_new_status ON candidate_status_history (new_status)",
        "CREATE INDEX IF NOT EXISTS ix_candidate_status_history_changed_by_user_id ON candidate_status_history (changed_by_user_id)",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS interview_format VARCHAR(32) NOT NULL DEFAULT 'online'",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(1000)",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS meeting_location VARCHAR(500)",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS scheduling_comment VARCHAR(2000)",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS requested_by_manager_id UUID",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS candidate_invite_status VARCHAR(32) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS manager_invite_status VARCHAR(32) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS confirmed_candidate_at TIMESTAMPTZ",
        "ALTER TABLE IF EXISTS interview_sessions ADD COLUMN IF NOT EXISTS confirmed_manager_at TIMESTAMPTZ",
        """
        CREATE TABLE IF NOT EXISTS interview_requests (
            id UUID PRIMARY KEY,
            candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            vacancy_id UUID REFERENCES vacancies(id) ON DELETE SET NULL,
            manager_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            hr_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            requested_mode VARCHAR(16) NOT NULL,
            requested_format VARCHAR(32) NOT NULL DEFAULT 'online',
            requested_time TIMESTAMPTZ,
            comment VARCHAR(2000),
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            review_comment VARCHAR(2000),
            reviewed_at TIMESTAMPTZ,
            created_interview_session_id UUID REFERENCES interview_sessions(id) ON DELETE SET NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_interview_requests_candidate_id ON interview_requests (candidate_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_requests_vacancy_id ON interview_requests (vacancy_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_requests_manager_user_id ON interview_requests (manager_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_requests_hr_user_id ON interview_requests (hr_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_requests_status ON interview_requests (status)",
        "ALTER TABLE IF EXISTS vacancies ADD COLUMN IF NOT EXISTS organization_id UUID",
        """
        CREATE TABLE IF NOT EXISTS vacancy_applications (
            id UUID PRIMARY KEY,
            vacancy_id UUID NOT NULL REFERENCES vacancies(id) ON DELETE CASCADE,
            candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status VARCHAR(64) NOT NULL DEFAULT 'applied',
            cover_letter_text VARCHAR(4000),
            note VARCHAR(2000),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_vacancy_applications_vacancy_candidate ON vacancy_applications (vacancy_id, candidate_id)",
        "CREATE INDEX IF NOT EXISTS ix_vacancy_applications_vacancy_id ON vacancy_applications (vacancy_id)",
        "CREATE INDEX IF NOT EXISTS ix_vacancy_applications_candidate_id ON vacancy_applications (candidate_id)",
        "CREATE INDEX IF NOT EXISTS ix_vacancy_applications_status ON vacancy_applications (status)",
        """
        CREATE TABLE IF NOT EXISTS profile_options (
            id UUID PRIMARY KEY,
            option_type VARCHAR(64) NOT NULL,
            value VARCHAR(255) NOT NULL,
            normalized_value VARCHAR(255) NOT NULL,
            created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_options_type_normalized ON profile_options (option_type, normalized_value)",
        "CREATE INDEX IF NOT EXISTS ix_profile_options_option_type ON profile_options (option_type)",
    ]

    for stmt in statements:
        await conn.execute(text(stmt))
