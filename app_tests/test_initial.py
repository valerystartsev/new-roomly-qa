import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models import Equipment, Office, Room, User
from app.seed import seed


@pytest.fixture
def client():
    with TestClient(app) as instance:
        yield instance


def login(client, email, password):
    result = client.post('/api/v1/sessions', json={'email': email, 'password': password})
    assert result.status_code == 200
    return {'X-CSRF-Token': result.json()['csrf_token']}


def test_seed_is_repeatable_and_preserves_admin():
    with SessionLocal() as db:
        before = db.scalar(select(User.password_hash).where(User.email == os.environ['INITIAL_ADMIN_EMAIL'].lower()))
    seed()
    seed()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Office)) == 4
        assert db.scalar(select(func.count()).select_from(Room)) == 12
        assert db.scalar(select(func.count()).select_from(Equipment)) == 16
        assert db.scalar(select(User.password_hash).where(User.email == os.environ['INITIAL_ADMIN_EMAIL'].lower())) == before


def test_user_lifecycle_and_permissions(client):
    assert client.get('/api/v1/users/me').status_code == 401
    headers = login(client, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    assert client.post('/api/v1/admin/users', json={}).status_code == 403
    payload = {'email': f'{uuid.uuid4().hex}@example.test', 'display_name': 'Test User', 'password': 'initial-password-123', 'role': 'user'}
    created = client.post('/api/v1/admin/users', json=payload, headers=headers)
    assert created.status_code == 201
    user_id = created.json()['id']
    assert 'password_hash' not in created.json()
    assert client.delete('/api/v1/sessions/current', headers=headers).status_code == 200
    user_headers = login(client, payload['email'], payload['password'])
    assert client.get('/api/v1/admin/users').status_code == 403
    assert client.post('/api/v1/users/me/change-password', json={'current_password': 'wrong-password', 'new_password': 'changed-password-123'}, headers=user_headers).status_code == 400
    assert client.post('/api/v1/users/me/change-password', json={'current_password': payload['password'], 'new_password': 'changed-password-123'}).status_code == 403
    assert client.post('/api/v1/admin/users', json=payload, headers=user_headers).status_code == 403
    changed = client.post('/api/v1/users/me/change-password', json={'current_password': payload['password'], 'new_password': 'changed-password-123'}, headers=user_headers)
    assert changed.status_code == 200
    assert client.get('/api/v1/users/me').status_code == 401
    headers = login(client, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    assert client.post(f'/api/v1/admin/users/{user_id}/reset-password', json={'password': 'reset-password-123'}, headers=headers).status_code == 200
    assert client.delete('/api/v1/sessions/current', headers=headers).status_code == 200
    assert login(client, payload['email'], 'reset-password-123')
