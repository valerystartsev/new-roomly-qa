from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import engine


def test_room_and_equipment_intervals_and_cancellation():
    with engine.connect() as db:
        transaction = db.begin()
        try:
            organizer = db.scalar(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1"))
            room, office = db.execute(text('SELECT id, office_id FROM rooms ORDER BY id LIMIT 1')).one()
            equipment = db.scalar(text('SELECT id FROM equipment WHERE office_id = :office ORDER BY id LIMIT 1'), {'office': office})
            start = datetime(2099, 1, 1, 12, tzinfo=timezone.utc)

            def add_booking(begin):
                return db.scalar(text('''INSERT INTO bookings (organizer_id, start_at, end_at, reference_timezone, status)
                    VALUES (:user, :start, :end, 'UTC', 'active') RETURNING id'''),
                    {'user': organizer, 'start': begin, 'end': begin + timedelta(hours=1)})

            def add_room(booking, begin):
                return db.scalar(text('''INSERT INTO booking_rooms (booking_id, room_id, office_id, participants, start_at, end_at, status)
                    VALUES (:booking, :room, :office, 1, :start, :end, 'active') RETURNING id'''),
                    {'booking': booking, 'room': room, 'office': office, 'start': begin, 'end': begin + timedelta(hours=1)})

            first = add_booking(start)
            first_room = add_room(first, start)
            db.execute(text('''INSERT INTO equipment_allocations (booking_room_id, equipment_id, office_id, start_at, end_at, status)
                VALUES (:room, :equipment, :office, :start, :end, 'active')'''),
                {'room': first_room, 'equipment': equipment, 'office': office, 'start': start, 'end': start + timedelta(hours=1)})
            other_room = db.scalar(text('SELECT id FROM rooms WHERE office_id = :office AND id <> :room ORDER BY id LIMIT 1'), {'office': office, 'room': room})
            competing = add_booking(start)
            competing_room = db.scalar(text('''INSERT INTO booking_rooms (booking_id, room_id, office_id, participants, start_at, end_at, status)
                VALUES (:booking, :room, :office, 1, :start, :end, 'active') RETURNING id'''),
                {'booking': competing, 'room': other_room, 'office': office, 'start': start, 'end': start + timedelta(hours=1)})
            with pytest.raises(IntegrityError):
                with db.begin_nested():
                    db.execute(text('''INSERT INTO equipment_allocations (booking_room_id, equipment_id, office_id, start_at, end_at, status)
                        VALUES (:room, :equipment, :office, :start, :end, 'active')'''),
                        {'room': competing_room, 'equipment': equipment, 'office': office, 'start': start, 'end': start + timedelta(hours=1)})
            overlap = add_booking(start)
            with pytest.raises(IntegrityError):
                with db.begin_nested():
                    add_room(overlap, start)
            adjacent = add_booking(start + timedelta(hours=1))
            add_room(adjacent, start + timedelta(hours=1))
            db.execute(text("UPDATE bookings SET status = 'cancelled', cancelled_at = now() WHERE id = :id"), {'id': first})
            assert db.scalar(text('SELECT status FROM equipment_allocations WHERE booking_room_id = :id'), {'id': first_room}) == 'cancelled'
            add_room(overlap, start)
        finally:
            transaction.rollback()
