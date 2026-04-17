import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv('HIRE_TEST_BASE_URL', 'http://localhost:8000/api/v1')
RUN_LIVE_SMOKE = os.getenv('HIRE_RUN_LIVE_SMOKE', '').strip().lower() in {'1', 'true', 'yes'}
pytestmark = pytest.mark.skipif(
    not RUN_LIVE_SMOKE,
    reason='Live API smoke tests are disabled by default. Set HIRE_RUN_LIVE_SMOKE=true to enable.',
)


def _register_candidate() -> dict:
    email = f"smoke_{uuid.uuid4().hex[:12]}@example.com"
    payload = {
        'email': email,
        'password': 'StrongPass123!',
        'full_name': 'Smoke Candidate',
    }
    response = httpx.post(f'{BASE_URL}/auth/register', json=payload, timeout=20)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body.get('access_token')
    assert body.get('refresh_token')
    return body


def test_auth_lifecycle_candidate():
    tokens = _register_candidate()

    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    me_response = httpx.get(f'{BASE_URL}/auth/me', headers=headers, timeout=20)
    assert me_response.status_code == 200, me_response.text

    me = me_response.json()
    assert me['role'] == 'candidate'
    assert me['is_active'] is True


def test_registration_rejects_role_escalation_payload():
    email = f"smoke_role_{uuid.uuid4().hex[:12]}@example.com"
    payload = {
        'email': email,
        'password': 'StrongPass123!',
        'full_name': 'Role Escalation Candidate',
        'role': 'admin',
    }
    response = httpx.post(f'{BASE_URL}/auth/register', json=payload, timeout=20)
    assert response.status_code == 422, response.text


def test_candidate_can_create_own_candidate_profile_once():
    tokens = _register_candidate()

    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    payload = {
        'full_name': 'Self Candidate Profile',
        'email': 'self-profile@example.com',
        'headline': 'backend engineer',
        'status': 'new',
        'skills': [],
        'experience': [],
        'education': [],
        'projects': [],
        'languages': [],
    }
    response = httpx.post(f'{BASE_URL}/candidates', json=payload, headers=headers, timeout=20)
    assert response.status_code == 201, response.text

    duplicate = httpx.post(f'{BASE_URL}/candidates', json=payload, headers=headers, timeout=20)
    assert duplicate.status_code == 409, duplicate.text
