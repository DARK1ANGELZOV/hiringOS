from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.router import api_router
from app.api.routes.vacancies import _build_match
from app.core.security import hash_password
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_change_password_success_revokes_sessions():
    user_id = uuid4()
    user = SimpleNamespace(id=user_id, hashed_password=hash_password('StrongPass123!'))

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user
    user_repo.db = SimpleNamespace(flush=AsyncMock())

    refresh_repo = AsyncMock()

    service = AuthService(
        user_repository=user_repo,
        refresh_repository=refresh_repo,
        organization_repository=AsyncMock(),
    )

    await service.change_password(
        user_id=user_id,
        current_password='StrongPass123!',
        new_password='StrongPass456!',
    )

    refresh_repo.revoke_all_for_user.assert_awaited_once()
    assert refresh_repo.revoke_all_for_user.await_args.kwargs['reason'] == 'password_changed'


@pytest.mark.asyncio
async def test_change_password_rejects_invalid_current_password():
    user_id = uuid4()
    user = SimpleNamespace(id=user_id, hashed_password=hash_password('StrongPass123!'))

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user
    user_repo.db = SimpleNamespace(flush=AsyncMock())

    service = AuthService(
        user_repository=user_repo,
        refresh_repository=AsyncMock(),
        organization_repository=AsyncMock(),
    )

    with pytest.raises(HTTPException):
        await service.change_password(
            user_id=user_id,
            current_password='WrongPassword111!',
            new_password='StrongPass456!',
        )


def test_vacancy_match_scoring_uses_skill_overlap():
    vacancy = SimpleNamespace(stack_json=['Python', 'FastAPI', 'PostgreSQL'])
    candidate = SimpleNamespace(
        skills_raw='Python, SQL, Docker',
        competencies_raw='FastAPI',
        skills=[{'name': 'PostgreSQL'}],
    )
    match = _build_match(vacancy, candidate)
    assert match['score_percent'] == 100.0
    assert 'python' in match['matched_skills']
    assert not match['missing_skills']


def test_api_router_contains_new_candidate_and_vacancy_routes():
    path_to_methods: dict[str, set[str]] = {}
    for route in api_router.routes:
        methods = getattr(route, 'methods', None)
        path = getattr(route, 'path', None)
        if not methods or not path:
            continue
        path_to_methods.setdefault(path, set()).update(methods)

    required = {
        '/auth/change-password': {'POST'},
        '/resumes/parse-text/{candidate_id}': {'POST'},
        '/candidates/profile-options/programming-languages': {'GET', 'POST'},
        '/vacancies': {'GET'},
        '/vacancies/{vacancy_id:uuid}/apply': {'POST'},
        '/vacancies/my-applications': {'GET'},
        '/vacancies/applications': {'GET'},
        '/vacancies/applications/{application_id:uuid}/status': {'PATCH'},
    }

    for path, methods in required.items():
        assert path in path_to_methods, f'Missing route: {path}'
        assert methods.issubset(path_to_methods[path]), f'Route {path} missing methods {methods - path_to_methods[path]}'
