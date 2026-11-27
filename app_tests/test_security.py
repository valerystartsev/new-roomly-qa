from datetime import datetime, timedelta, timezone
import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app, login_attempts
from app.models import Session, User
from app.security import digest_token, verify_password


def login(client, email, password):
    return client.post('/api/v1/sessions', json={'email': email, 'password': password})


def test_csrf_cookie_rotation_and_expiry():
    login_attempts.clear()
    with TestClient(app) as client:
        result = login(client, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
        assert result.status_code == 200
        assert 'HttpOnly' in result.headers['set-cookie']
        assert 'SameSite=strict' in result.headers['set-cookie']
        original = result.json()['csrf_token']
        renewed = client.get('/api/v1/sessions/current').json()['csrf_token']
        assert renewed != original
        assert client.delete('/api/v1/sessions/current', headers={'X-CSRF-Token': original}).status_code == 403
        token = client.cookies.get('roomly_session')
        with SessionLocal.begin() as db:
            session = db.get(Session, digest_token(token))
            session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert client.get('/api/v1/users/me').status_code == 401


def test_admin_normalizes_email_hashes_password_and_revokes_sessions():
    login_attempts.clear()
    with TestClient(app) as administrator, TestClient(app) as first, TestClient(app) as second:
        response = login(administrator, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
        headers = {'X-CSRF-Token': response.json()['csrf_token']}
        email = f'{uuid.uuid4().hex}@example.test'
        password = 'initial-password-123'
        created = administrator.post('/api/v1/admin/users', headers=headers, json={
            'email': f' {email.upper()} ', 'display_name': 'Example User', 'password': password,
        })
        assert created.status_code == 201
        assert created.json()['email'] == email
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user.password_hash != password
            assert verify_password(password, user.password_hash)
        assert login(first, email, password).status_code == 200
        assert login(second, email, password).status_code == 200
        reset = administrator.post(f"/api/v1/admin/users/{created.json()['id']}/reset-password", headers=headers, json={'password': 'replacement-password-123'})
        assert reset.status_code == 200
        assert first.get('/api/v1/users/me').status_code == 401
        assert second.get('/api/v1/users/me').status_code == 401
        assert login(first, email, password).status_code == 401
        assert login(first, email, 'replacement-password-123').status_code == 200


def test_login_rate_limit():
    login_attempts.clear()
    with TestClient(app) as client:
        for _ in range(10):
            assert login(client, 'missing@example.test', 'wrong-password').status_code == 401
        assert login(client, 'missing@example.test', 'wrong-password').status_code == 429
    login_attempts.clear()
