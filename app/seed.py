import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Equipment, Office, Room, User
from app.security import hash_password

OFFICES = [('New York', 'America/New_York'), ('London', 'Europe/London'), ('Moscow', 'Europe/Moscow'), ('Tokyo', 'Asia/Tokyo')]
ROOMS = [('Small', 'small', 4), ('Medium', 'medium', 10), ('Large', 'large', 20)]


def seed():
    with SessionLocal.begin() as db:
        for name, timezone in OFFICES:
            office = db.scalar(select(Office).where(Office.name == name))
            if office is None:
                office = Office(name=name, timezone=timezone)
                db.add(office)
                db.flush()
            for room_name, category, capacity in ROOMS:
                if db.scalar(select(Room.id).where(Room.office_id == office.id, Room.name == room_name)) is None:
                    db.add(Room(office_id=office.id, name=room_name, category=category, capacity=capacity))
            for kind in ('projector', 'speakerphone'):
                for number in (1, 2):
                    label = f'{kind}-{number}'
                    if db.scalar(select(Equipment.id).where(Equipment.office_id == office.id, Equipment.label == label)) is None:
                        db.add(Equipment(office_id=office.id, type=kind, label=label))
        if db.scalar(select(User.id).where(User.role == 'admin')) is None:
            email = os.environ.get('INITIAL_ADMIN_EMAIL', '').strip().lower()
            password = os.environ.get('INITIAL_ADMIN_PASSWORD', '')
            if '@' not in email or not 12 <= len(password) <= 256:
                raise ValueError('Initial administrator email and password (12–256 characters) are required')
            db.add(User(email=email, display_name='Administrator', password_hash=hash_password(password), role='admin'))


if __name__ == '__main__':
    seed()
