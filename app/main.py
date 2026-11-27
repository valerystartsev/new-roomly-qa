import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session as DbSession

from app.database import SessionLocal
from app.models import Session, User
from app.security import digest_token, hash_password, verify_password
from app.resources import create_resource_router

app = FastAPI(title='Roomly API', version='0.1.0')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'true').lower() == 'true'
COOKIE_NAME = 'roomly_session'
login_attempts = {}
login_lock = Lock()


def db_session():
    with SessionLocal() as db:
        yield db


def current_session(request: Request, db: DbSession = Depends(db_session)):
    token = request.cookies.get(COOKIE_NAME, '')
    session = db.get(Session, digest_token(token)) if token else None
    if not session or session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, 'Authentication required')
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, 'Authentication required')
    return session, user


def authenticated(pair=Depends(current_session)):
    return pair[1]


def csrf(pair=Depends(current_session), x_csrf_token: str = Header(default='')):
    if not x_csrf_token or not hmac.compare_digest(pair[0].csrf_hash, digest_token(x_csrf_token)):
        raise HTTPException(403, 'Invalid CSRF token')
    return pair[1]


def admin(user=Depends(csrf)):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return user


def public_user(user):
    return {'id': user.id, 'email': user.email, 'display_name': user.display_name, 'role': user.role}


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class NewUser(Credentials):
    display_name: str = Field(min_length=1, max_length=120)
    role: str = 'user'


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class ResetPassword(BaseModel):
    password: str = Field(min_length=12, max_length=256)


def validate_user(data):
    email = data.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(data.password) < 12 or not data.display_name.strip() or data.role not in ('user', 'admin'):
        raise HTTPException(422, 'Invalid account data')
    return email


@app.get('/api/v1/health')
def health(db: DbSession = Depends(db_session)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok'}


@app.post('/api/v1/sessions')
def login(data: Credentials, request: Request, response: Response, db: DbSession = Depends(db_session)):
    ip = request.client.host if request.client else 'unknown'
    now = monotonic()
    with login_lock:
        login_attempts[ip] = [entry for entry in login_attempts.get(ip, []) if now - entry < 60]
        if len(login_attempts[ip]) >= 10:
            raise HTTPException(429, 'Too many login attempts')
        login_attempts[ip].append(now)
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if user is None or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Invalid credentials')
    token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(Session(token_hash=digest_token(token), user_id=user.id, csrf_hash=digest_token(csrf_token), expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=28800, path='/')
    return {'user': public_user(user), 'csrf_token': csrf_token}


@app.get('/api/v1/users/me')
def me(user=Depends(authenticated)):
    return public_user(user)


@app.get('/api/v1/sessions/current')
def session_info(pair=Depends(current_session), db: DbSession = Depends(db_session)):
    token = secrets.token_urlsafe(32)
    pair[0].csrf_hash = digest_token(token)
    db.commit()
    return {'user': public_user(pair[1]), 'csrf_token': token}


@app.delete('/api/v1/sessions/current')
def logout(response: Response, pair=Depends(current_session), user=Depends(csrf), db: DbSession = Depends(db_session)):
    db.delete(pair[0])
    db.commit()
    response.delete_cookie(COOKIE_NAME, path='/', secure=COOKIE_SECURE, httponly=True, samesite='strict')
    return {'ok': True}


@app.post('/api/v1/users/me/change-password')
def change_password(data: PasswordChange, user=Depends(csrf), db: DbSession = Depends(db_session)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, 'Invalid current password')
    user.password_hash = hash_password(data.new_password)
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.commit()
    return {'ok': True}


@app.get('/api/v1/admin/users')
def list_users(user=Depends(authenticated), db: DbSession = Depends(db_session)):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return [public_user(item) for item in db.scalars(select(User).order_by(User.id))]


@app.post('/api/v1/admin/users', status_code=201)
def create_user(data: NewUser, actor=Depends(admin), db: DbSession = Depends(db_session)):
    email = validate_user(data)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, 'Email already exists')
    user = User(email=email, display_name=data.display_name.strip(), role=data.role, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return public_user(user)


@app.post('/api/v1/admin/users/{user_id}/reset-password')
def reset_password(user_id: int, data: ResetPassword, actor=Depends(admin), db: DbSession = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    user.password_hash = hash_password(data.password)
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.commit()
    return {'ok': True}


app.include_router(create_resource_router(db_session, authenticated, admin))
app.mount('/account', StaticFiles(directory='app/static', html=True), name='account')
