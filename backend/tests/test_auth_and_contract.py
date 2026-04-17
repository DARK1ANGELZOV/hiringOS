from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.api.router import api_router
from app.models.enums import UserRole
from app.schemas.auth import RegisterRequest, TokenPair
from app.services.auth_service import AuthService


def _token_pair() -> TokenPair:
    return TokenPair(
        access_token='access',
        access_token_expires_at='2030-01-01T00:00:00Z',
        refresh_token='refresh',
        refresh_token_expires_at='2030-01-02T00:00:00Z',
    )


@pytest.mark.asyncio
async def test_register_creates_candidate_when_bootstrap_closed():
    user = SimpleNamespace(id=uuid4(), email='candidate@example.com', full_name='Candidate', role=UserRole.CANDIDATE)
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    user_repo.create.return_value = user
    user_repo.db = SimpleNamespace(flush=AsyncMock())

    service = AuthService(
        user_repository=user_repo,
        refresh_repository=AsyncMock(),
        organization_repository=AsyncMock(),
    )
    service.organization_service.bootstrap_available = AsyncMock(return_value=False)
    service._issue_tokens = AsyncMock(return_value=_token_pair())

    await service.register(RegisterRequest(email='candidate@example.com', password='StrongPass123!', full_name='Candidate'))

    created_kwargs = user_repo.create.await_args.kwargs
    assert created_kwargs['role'] == UserRole.CANDIDATE
    assert user.role == UserRole.CANDIDATE
    assert service._issue_tokens.await_args.kwargs['role'] == UserRole.CANDIDATE.value
    assert service._issue_tokens.await_args.kwargs['org_id'] is None


@pytest.mark.asyncio
async def test_register_bootstrap_promotes_first_user_to_admin_owner():
    user = SimpleNamespace(id=uuid4(), email='owner@example.com', full_name='Owner', role=UserRole.CANDIDATE)
    bootstrap_org_id = uuid4()

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    user_repo.create.return_value = user
    user_repo.db = SimpleNamespace(flush=AsyncMock())

    service = AuthService(
        user_repository=user_repo,
        refresh_repository=AsyncMock(),
        organization_repository=AsyncMock(),
    )
    service.organization_service.bootstrap_available = AsyncMock(return_value=True)
    service.organization_service.create_bootstrap_for_user = AsyncMock(return_value=SimpleNamespace(id=bootstrap_org_id))
    service._issue_tokens = AsyncMock(return_value=_token_pair())

    await service.register(RegisterRequest(email='owner@example.com', password='StrongPass123!', full_name='Owner'))

    assert user.role == UserRole.ADMIN
    assert service._issue_tokens.await_args.kwargs['role'] == UserRole.ADMIN.value
    assert service._issue_tokens.await_args.kwargs['org_id'] == str(bootstrap_org_id)


def test_api_router_contains_required_security_and_business_routes():
    path_to_methods: dict[str, set[str]] = {}
    for route in api_router.routes:
        methods = getattr(route, 'methods', None)
        path = getattr(route, 'path', None)
        if not methods or not path:
            continue
        path_to_methods.setdefault(path, set()).update(methods)

    required = {
        '/auth/register': {'POST'},
        '/auth/invite/accept': {'POST'},
        '/organizations/{organization_id}/invites': {'POST'},
        '/documents/item/{document_id}/download-url': {'GET'},
        '/documents/item/{document_id}/replace': {'PUT'},
        '/documents/item/{document_id}': {'DELETE'},
        '/candidates/{candidate_id:uuid}/status-history': {'GET'},
        '/interviews/requests': {'GET', 'POST'},
        '/interviews/requests/{request_id}/review': {'PATCH'},
        '/interviews/{session_id:uuid}/schedule': {'PATCH'},
        '/interviews/{session_id:uuid}/invite/decision': {'POST'},
        '/admin/users/{user_id}/role': {'PATCH'},
        '/admin/users/{user_id}/memberships': {'GET', 'POST'},
        '/admin/users/{user_id}/memberships/{membership_id}': {'PATCH', 'DELETE'},
        '/admin/users/{user_id}/sessions': {'GET'},
    }

    for path, methods in required.items():
        assert path in path_to_methods, f'Missing route: {path}'
        assert methods.issubset(path_to_methods[path]), f'Route {path} missing methods {methods - path_to_methods[path]}'
