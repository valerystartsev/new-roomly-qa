from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Equipment, Office, Room

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Timezone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Category = Literal['small', 'medium', 'large']
EquipmentType = Literal['projector', 'speakerphone']


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class OfficeData(InputModel):
    name: Name
    timezone: Timezone

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Invalid IANA time zone') from None
        return value


class OfficeUpdate(InputModel):
    name: Name | None = None
    timezone: Timezone | None = None
    active: bool | None = None

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            return OfficeData.valid_timezone(value)
        return value


class RoomData(InputModel):
    office_id: int = Field(gt=0)
    name: Name
    category: Category
    capacity: int = Field(gt=0, strict=True)


class RoomUpdate(InputModel):
    name: Name | None = None
    category: Category | None = None
    capacity: int | None = Field(default=None, gt=0, strict=True)
    active: bool | None = None


class EquipmentData(InputModel):
    office_id: int = Field(gt=0)
    type: EquipmentType
    label: Name


class EquipmentUpdate(InputModel):
    label: Name | None = None
    active: bool | None = None


def fields(resource, names):
    return {name: getattr(resource, name) for name in names}


OFFICE_FIELDS = ('id', 'name', 'timezone', 'active')
ROOM_FIELDS = ('id', 'office_id', 'name', 'category', 'capacity', 'active')
EQUIPMENT_FIELDS = ('id', 'office_id', 'type', 'label', 'active')


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Resource conflicts with existing data') from None


def get_office(db, office_id, lock=False):
    query = select(Office).where(Office.id == office_id)
    office = db.scalar(query.with_for_update() if lock else query)
    if office is None:
        raise HTTPException(404, 'Office not found')
    return office


def get_resource(db, model, resource_id):
    resource = db.scalar(select(model).where(model.id == resource_id).with_for_update())
    if resource is None:
        raise HTTPException(404, 'Resource not found')
    return resource


def ensure_active_office(db, office_id):
    office = get_office(db, office_id, lock=True)
    if not office.active:
        raise HTTPException(409, 'Office is inactive')


def update_values(data):
    values = data.model_dump(exclude_unset=True)
    if not values or any(value is None for value in values.values()):
        raise HTTPException(422, 'Provide non-null fields to update')
    return values


def ensure_no_active_bookings(db, resource, resource_id):
    clauses = {
        'office': 'br.office_id = :id',
        'room': 'br.room_id = :id',
        'equipment': 'ea.equipment_id = :id',
    }
    joins = 'JOIN equipment_allocations ea ON ea.booking_room_id = br.id' if resource == 'equipment' else ''
    query = text(f'''SELECT 1 FROM booking_rooms br {joins}
        WHERE {clauses[resource]} AND br.status = 'active' AND br.end_at > now() LIMIT 1''')
    if db.execute(query, {'id': resource_id}).first():
        raise HTTPException(409, 'Resource has current or future bookings')


def create_resource_router(db_session, authenticated, admin):
    router = APIRouter(prefix='/api/v1')

    @router.get('/offices')
    def offices(user=Depends(authenticated), db: Session = Depends(db_session)):
        return [fields(office, OFFICE_FIELDS) for office in db.scalars(select(Office).order_by(Office.id))]

    @router.get('/offices/{office_id}/rooms')
    def rooms(office_id: int, user=Depends(authenticated), db: Session = Depends(db_session)):
        get_office(db, office_id)
        return [fields(room, ROOM_FIELDS) for room in db.scalars(select(Room).where(Room.office_id == office_id).order_by(Room.id))]

    @router.get('/offices/{office_id}/equipment')
    def equipment(office_id: int, user=Depends(authenticated), db: Session = Depends(db_session)):
        get_office(db, office_id)
        return [fields(unit, EQUIPMENT_FIELDS) for unit in db.scalars(select(Equipment).where(Equipment.office_id == office_id).order_by(Equipment.id))]

    @router.post('/admin/offices', status_code=201)
    def create_office(data: OfficeData, user=Depends(admin), db: Session = Depends(db_session)):
        office = Office(**data.model_dump())
        db.add(office)
        commit(db)
        return fields(office, OFFICE_FIELDS)

    @router.post('/admin/rooms', status_code=201)
    def create_room(data: RoomData, user=Depends(admin), db: Session = Depends(db_session)):
        ensure_active_office(db, data.office_id)
        room = Room(**data.model_dump())
        db.add(room)
        commit(db)
        return fields(room, ROOM_FIELDS)

    @router.post('/admin/equipment', status_code=201)
    def create_equipment(data: EquipmentData, user=Depends(admin), db: Session = Depends(db_session)):
        ensure_active_office(db, data.office_id)
        unit = Equipment(**data.model_dump())
        db.add(unit)
        commit(db)
        return fields(unit, EQUIPMENT_FIELDS)

    @router.patch('/admin/offices/{office_id}')
    def update_office(office_id: int, data: OfficeUpdate, user=Depends(admin), db: Session = Depends(db_session)):
        values = update_values(data)
        office = get_office(db, office_id, lock=True)
        if values.get('active') is False and office.active:
            ensure_no_active_bookings(db, 'office', office_id)
        for key, value in values.items():
            setattr(office, key, value)
        commit(db)
        return fields(office, OFFICE_FIELDS)

    @router.patch('/admin/rooms/{room_id}')
    def update_room(room_id: int, data: RoomUpdate, user=Depends(admin), db: Session = Depends(db_session)):
        values = update_values(data)
        room = get_resource(db, Room, room_id)
        if values.get('active') is True:
            ensure_active_office(db, room.office_id)
        if values.get('active') is False and room.active:
            ensure_no_active_bookings(db, 'room', room_id)
        for key, value in values.items():
            setattr(room, key, value)
        commit(db)
        return fields(room, ROOM_FIELDS)

    @router.patch('/admin/equipment/{equipment_id}')
    def update_equipment(equipment_id: int, data: EquipmentUpdate, user=Depends(admin), db: Session = Depends(db_session)):
        values = update_values(data)
        unit = get_resource(db, Equipment, equipment_id)
        if values.get('active') is True:
            ensure_active_office(db, unit.office_id)
        if values.get('active') is False and unit.active:
            ensure_no_active_bookings(db, 'equipment', equipment_id)
        for key, value in values.items():
            setattr(unit, key, value)
        commit(db)
        return fields(unit, EQUIPMENT_FIELDS)

    return router
