"""Create the initial user and reference data schema."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users', sa.Column('id', sa.Integer, primary_key=True), sa.Column('email', sa.String(254), nullable=False, unique=True), sa.Column('display_name', sa.String(120), nullable=False), sa.Column('password_hash', sa.String(256), nullable=False), sa.Column('role', sa.String(20), nullable=False), sa.Column('active', sa.Boolean, nullable=False), sa.CheckConstraint("role IN ('admin', 'user')", name='user_role'))
    op.create_table('sessions', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('csrf_hash', sa.String(64), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_table('offices', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(120), nullable=False, unique=True), sa.Column('timezone', sa.String(64), nullable=False), sa.Column('active', sa.Boolean, nullable=False))
    op.create_table('rooms', sa.Column('id', sa.Integer, primary_key=True), sa.Column('office_id', sa.Integer, sa.ForeignKey('offices.id'), nullable=False), sa.Column('name', sa.String(120), nullable=False), sa.Column('category', sa.String(20), nullable=False), sa.Column('capacity', sa.Integer, nullable=False), sa.Column('active', sa.Boolean, nullable=False), sa.UniqueConstraint('office_id', 'name'), sa.CheckConstraint('capacity > 0', name='room_capacity'), sa.CheckConstraint("category IN ('small', 'medium', 'large')", name='room_category'))
    op.create_index('ix_rooms_office_id', 'rooms', ['office_id'])
    op.create_table('equipment', sa.Column('id', sa.Integer, primary_key=True), sa.Column('office_id', sa.Integer, sa.ForeignKey('offices.id'), nullable=False), sa.Column('type', sa.String(20), nullable=False), sa.Column('label', sa.String(120), nullable=False), sa.Column('active', sa.Boolean, nullable=False), sa.UniqueConstraint('office_id', 'label'), sa.CheckConstraint("type IN ('projector', 'speakerphone')", name='equipment_type'))
    op.create_index('ix_equipment_office_id', 'equipment', ['office_id'])


def downgrade():
    op.drop_table('equipment')
    op.drop_table('rooms')
    op.drop_table('offices')
    op.drop_table('sessions')
    op.drop_table('users')
