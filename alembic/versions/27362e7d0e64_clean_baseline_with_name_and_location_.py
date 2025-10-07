"""clean baseline with name and location fields

Revision ID: 27362e7d0e64
Revises: 
Create Date: 2025-10-07 13:53:37.730703+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27362e7d0e64'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
        sa.UniqueConstraint('username', name=op.f('uq_users_username'))
    )
    
    # Create sites table
    op.create_table('sites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_sites_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_sites'))
    )
    
    # Create meters table with name and location fields
    op.create_table('meters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('serial_number', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], name=op.f('fk_meters_site_id_sites')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_meters')),
        sa.UniqueConstraint('serial_number', name=op.f('uq_meters_serial_number'))
    )
    
    # Create tariffs table
    op.create_table('tariffs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('price_per_kwh', sa.Float(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], name=op.f('fk_tariffs_site_id_sites')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tariffs'))
    )
    
    # Create energy_exported table
    op.create_table('energy_exported',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('measure_value', sa.Float(), nullable=False),
        sa.Column('period', sa.String(length=10), nullable=True),
        sa.Column('meter_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_energy_exported_meter_id_meters')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_energy_exported'))
    )
    op.create_index(op.f('ix_energy_exported_timestamp'), 'energy_exported', ['timestamp'], unique=False)
    
    # Create energy_imported table
    op.create_table('energy_imported',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('measure_value', sa.Float(), nullable=False),
        sa.Column('period', sa.String(length=10), nullable=True),
        sa.Column('meter_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_energy_imported_meter_id_meters')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_energy_imported'))
    )
    op.create_index(op.f('ix_energy_imported_timestamp'), 'energy_imported', ['timestamp'], unique=False)
    
    # Create energy_reactive table
    op.create_table('energy_reactive',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('imported_kvarh', sa.Float(), nullable=False),
        sa.Column('exported_kvarh', sa.Float(), nullable=False),
        sa.Column('meter_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_energy_reactive_meter_id_meters')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_energy_reactive'))
    )
    op.create_index(op.f('ix_energy_reactive_timestamp'), 'energy_reactive', ['timestamp'], unique=False)
    
    # Create max_power table
    op.create_table('max_power',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('measure_value', sa.Float(), nullable=False),
        sa.Column('meter_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['meter_id'], ['meters.id'], name=op.f('fk_max_power_meter_id_meters')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_max_power'))
    )
    op.create_index(op.f('ix_max_power_timestamp'), 'max_power', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_max_power_timestamp'), table_name='max_power')
    op.drop_table('max_power')
    op.drop_index(op.f('ix_energy_reactive_timestamp'), table_name='energy_reactive')
    op.drop_table('energy_reactive')
    op.drop_index(op.f('ix_energy_imported_timestamp'), table_name='energy_imported')
    op.drop_table('energy_imported')
    op.drop_index(op.f('ix_energy_exported_timestamp'), table_name='energy_exported')
    op.drop_table('energy_exported')
    op.drop_table('tariffs')
    op.drop_table('meters')
    op.drop_table('sites')
    op.drop_table('users')
