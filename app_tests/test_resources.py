import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.database import SessionLocal
from app.main import app, login_attempts
from app.models import Equipment, Office, Room, User


@pytest.fixture
def context():
    login_attempts.clear()
    with TestClient(app) as admin, TestClient(app) as user:
        result = admin.post('/api/v1/sessions', json={'email': os.environ['INITIAL_ADMIN_EMAIL'], 'password': os.environ['INITIAL_ADMIN_PASSWORD']})
        assert result.status_code == 200
        headers = {'X-CSRF-Token': result.json()['csrf_token']}
        email = f'{uuid.uuid4().hex}@example.test'
        created = admin.post('/api/v1/admin/users', headers=headers, json={'email': email, 'password': 'initial-password-123', 'display_name': 'Test User'})
        assert created.status_code == 201
        user_id = created.json()['id']
        login = user.post('/api/v1/sessions', json={'email': email, 'password': 'initial-password-123'})
        assert login.status_code == 200
        user_headers = {'X-CSRF-Token': login.json()['csrf_token']}
        created_offices = []
        yield admin, headers, user, user_headers, created_offices
        with SessionLocal.begin() as db:
            for office_id in created_offices:
                db.execute(delete(Equipment).where(Equipment.office_id == office_id))
                db.execute(delete(Room).where(Room.office_id == office_id))
                db.execute(delete(Office).where(Office.id == office_id))
            db.execute(delete(User).where(User.id == user_id))
    login_attempts.clear()


def office(admin, headers, ids):
    response = admin.post('/api/v1/admin/offices', headers=headers, json={'name': f'Office {uuid.uuid4().hex}', 'timezone': 'Europe/London'})
    assert response.status_code == 201
    ids.append(response.json()['id'])
    return response.json()


def test_resource_crud_authorization_and_validation(context):
    admin, headers, user, user_headers, ids = context
    assert TestClient(app).get('/api/v1/offices').status_code == 401
    assert user.post('/api/v1/admin/offices', headers=user_headers, json={'name': 'Forbidden', 'timezone': 'UTC'}).status_code == 403
    assert admin.post('/api/v1/admin/offices', json={'name': 'No CSRF', 'timezone': 'UTC'}).status_code == 403
    assert admin.post('/api/v1/admin/offices', headers=headers, json={'name': 'Invalid', 'timezone': 'Invalid/Zone'}).status_code == 422
    current = office(admin, headers, ids)
    office_id = current['id']
    assert any(item['id'] == office_id for item in user.get('/api/v1/offices').json())
    assert admin.post('/api/v1/admin/offices', headers=headers, json={'name': current['name'], 'timezone': 'UTC'}).status_code == 409
    assert admin.post('/api/v1/admin/rooms', headers=headers, json={'office_id': office_id, 'name': 'Bad', 'category': 'small', 'capacity': 0}).status_code == 422
    room = admin.post('/api/v1/admin/rooms', headers=headers, json={'office_id': office_id, 'name': 'Room A', 'category': 'small', 'capacity': 4})
    assert room.status_code == 201
    unit = admin.post('/api/v1/admin/equipment', headers=headers, json={'office_id': office_id, 'label': 'Projector A', 'type': 'projector'})
    assert unit.status_code == 201
    assert user.get(f'/api/v1/offices/{office_id}/rooms').json()[0]['capacity'] == 4
    assert user.get(f'/api/v1/offices/{office_id}/equipment').json()[0]['label'] == 'Projector A'
    assert admin.patch(f"/api/v1/admin/rooms/{room.json()['id']}", headers=headers, json={'capacity': 6, 'active': False}).json()['capacity'] == 6
    assert admin.patch(f"/api/v1/admin/equipment/{unit.json()['id']}", headers=headers, json={'label': 'Renamed', 'active': False}).json()['active'] is False
    assert admin.patch(f'/api/v1/admin/offices/{office_id}', headers=headers, json={'timezone': 'Invalid/Zone'}).status_code == 422
    assert admin.patch(f'/api/v1/admin/offices/{office_id}', headers=headers, json={'active': False}).status_code == 200
    assert admin.post('/api/v1/admin/rooms', headers=headers, json={'office_id': office_id, 'name': 'Blocked', 'category': 'small', 'capacity': 1}).status_code == 409
    assert admin.patch(f"/api/v1/admin/rooms/{room.json()['id']}", headers=headers, json={'active': True}).status_code == 409
    assert admin.patch(f'/api/v1/admin/offices/{office_id}', headers=headers, json={'active': True}).status_code == 200
    assert admin.patch(f"/api/v1/admin/rooms/{room.json()['id']}", headers=headers, json={'active': True}).status_code == 200
    assert admin.patch(f'/api/v1/admin/offices/{office_id}', headers=headers, json={'name': None}).status_code == 422


def test_deactivation_preserves_booked_resources(context):
    admin, headers, _, _, ids = context
    office_id = office(admin, headers, ids)['id']
    room_id = admin.post('/api/v1/admin/rooms', headers=headers, json={'office_id': office_id, 'name': 'Booked', 'category': 'small', 'capacity': 4}).json()['id']
    unit_id = admin.post('/api/v1/admin/equipment', headers=headers, json={'office_id': office_id, 'label': 'Booked', 'type': 'speakerphone'}).json()['id']
    start = datetime.now(timezone.utc) + timedelta(days=1)
    with SessionLocal.begin() as db:
        organizer = db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).scalar_one()
        booking = db.execute(text("INSERT INTO bookings (organizer_id, start_at, end_at, reference_timezone, status) VALUES (:user, :start, :end, 'UTC', 'active') RETURNING id"), {'user': organizer, 'start': start, 'end': start + timedelta(hours=1)}).scalar_one()
        booking_room = db.execute(text("INSERT INTO booking_rooms (booking_id, room_id, office_id, participants, start_at, end_at, status) VALUES (:booking, :room, :office, 1, :start, :end, 'active') RETURNING id"), {'booking': booking, 'room': room_id, 'office': office_id, 'start': start, 'end': start + timedelta(hours=1)}).scalar_one()
        db.execute(text("INSERT INTO equipment_allocations (booking_room_id, equipment_id, office_id, start_at, end_at, status) VALUES (:room, :equipment, :office, :start, :end, 'active')"), {'room': booking_room, 'equipment': unit_id, 'office': office_id, 'start': start, 'end': start + timedelta(hours=1)})
    try:
        for path in (f'/api/v1/admin/offices/{office_id}', f'/api/v1/admin/rooms/{room_id}', f'/api/v1/admin/equipment/{unit_id}'):
            assert admin.patch(path, headers=headers, json={'active': False}).status_code == 409
        assert user_resource_active(admin, office_id, room_id, unit_id)
    finally:
        with SessionLocal.begin() as db:
            db.execute(text('DELETE FROM equipment_allocations WHERE booking_room_id = :id'), {'id': booking_room})
            db.execute(text('DELETE FROM booking_rooms WHERE id = :id'), {'id': booking_room})
            db.execute(text('DELETE FROM bookings WHERE id = :id'), {'id': booking})


def user_resource_active(client, office_id, room_id, unit_id):
    return (any(x['id'] == office_id and x['active'] for x in client.get('/api/v1/offices').json())
            and any(x['id'] == room_id and x['active'] for x in client.get(f'/api/v1/offices/{office_id}/rooms').json())
            and any(x['id'] == unit_id and x['active'] for x in client.get(f'/api/v1/offices/{office_id}/equipment').json()))
