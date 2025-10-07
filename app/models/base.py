# app/models/base.py
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData

# naming convention helps Alembic autogenerate safe constraints
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

class Base(DeclarativeBase):
    """Unified declarative base for all SmartEnergy models."""
    metadata = metadata

    # automatically generate __tablename__ if not explicitly set
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
