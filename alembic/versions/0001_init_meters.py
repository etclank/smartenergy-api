# alembic/versions/0001_init_meters.py
"""init meters

Revision ID: 0001_init_meters
Revises:
Create Date: 2025-10-02 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_init_meters"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
    )
    op.create_index("ix_meters_id", "meters", ["id"])


def downgrade() -> None:
    op.drop_index("ix_meters_id", table_name="meters")
    op.drop_table("meters")
