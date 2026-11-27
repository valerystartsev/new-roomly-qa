import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Equipment, Office, Room


def test_room_capacity_and_reference_constraints():
    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as db:
            db.add(Room(office_id=99999999, name=uuid.uuid4().hex, category='small', capacity=4))
    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as db:
            office = Office(name=uuid.uuid4().hex, timezone='UTC')
            db.add(office)
            db.flush()
            db.add(Room(office_id=office.id, name='Invalid', category='small', capacity=0))


def test_equipment_type_constraint():
    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as db:
            office = Office(name=uuid.uuid4().hex, timezone='UTC')
            db.add(office)
            db.flush()
            db.add(Equipment(office_id=office.id, type='invalid', label='Invalid'))
