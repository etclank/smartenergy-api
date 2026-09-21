"""Validate a pre-Alembic schema and optionally stamp the baseline revision."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable, Mapping
from typing import Any, cast

from alembic import command
from alembic.config import Config
from sqlalchemy import UniqueConstraint, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base


def _column_names(items: Iterable[Mapping[str, Any]]) -> set[tuple[str, ...]]:
    column_sets: set[tuple[str, ...]] = set()
    for item in items:
        columns = cast(list[str], item.get("column_names") or [])
        column_sets.add(tuple(columns))
    return column_sets


def _inspect_schema(connection: Connection) -> list[str]:
    inspector = inspect(connection)
    expected_tables = set(Base.metadata.tables)
    actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
    issues: list[str] = []

    missing_tables = expected_tables - actual_tables
    unexpected_tables = actual_tables - expected_tables
    if missing_tables:
        issues.append(f"missing tables: {', '.join(sorted(missing_tables))}")
    if unexpected_tables:
        issues.append(f"unexpected tables: {', '.join(sorted(unexpected_tables))}")

    for table_name in sorted(expected_tables & actual_tables):
        table = Base.metadata.tables[table_name]
        actual_columns = {
            column["name"]: column for column in inspector.get_columns(table_name)
        }
        expected_columns = {column.name: column for column in table.columns}

        missing_columns = set(expected_columns) - set(actual_columns)
        unexpected_columns = set(actual_columns) - set(expected_columns)
        if missing_columns:
            issues.append(
                f"{table_name}: missing columns: {', '.join(sorted(missing_columns))}"
            )
        if unexpected_columns:
            issues.append(
                f"{table_name}: unexpected columns: {', '.join(sorted(unexpected_columns))}"
            )

        for column_name in sorted(set(expected_columns) & set(actual_columns)):
            expected = expected_columns[column_name]
            actual = actual_columns[column_name]
            actual_type = actual["type"]
            if actual_type._type_affinity is not expected.type._type_affinity:
                issues.append(f"{table_name}.{column_name}: incompatible type")
            if bool(actual["nullable"]) != expected.nullable:
                issues.append(f"{table_name}.{column_name}: incompatible nullability")

        expected_pk = tuple(column.name for column in table.primary_key.columns)
        actual_pk = tuple(
            inspector.get_pk_constraint(table_name)["constrained_columns"]
        )
        if actual_pk != expected_pk:
            issues.append(f"{table_name}: incompatible primary key")

        expected_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        actual_unique = _column_names(inspector.get_unique_constraints(table_name))
        if not expected_unique.issubset(actual_unique):
            issues.append(f"{table_name}: missing expected unique constraint")

        expected_indexes = {
            (tuple(column.name for column in index.columns), index.unique)
            for index in table.indexes
        }
        actual_indexes = {
            (tuple(index["column_names"]), bool(index["unique"]))
            for index in inspector.get_indexes(table_name)
        }
        if not expected_indexes.issubset(actual_indexes):
            issues.append(f"{table_name}: missing expected index")

        expected_foreign_keys = {
            (
                tuple(constraint.column_keys),
                constraint.referred_table.name,
                tuple(element.column.name for element in constraint.elements),
            )
            for constraint in table.foreign_key_constraints
        }
        actual_foreign_keys = {
            (
                tuple(foreign_key["constrained_columns"]),
                str(foreign_key["referred_table"]),
                tuple(foreign_key["referred_columns"]),
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        }
        if not expected_foreign_keys.issubset(actual_foreign_keys):
            issues.append(f"{table_name}: missing expected foreign key")

    return issues


async def find_schema_issues(database_url: str | None = None) -> list[str]:
    """Return compatibility problems without changing the target database."""
    url = database_url or settings.database_url
    if not url:
        return ["DATABASE_URL is required"]

    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_inspect_schema)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a pre-Alembic schema before adopting the baseline."
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="stamp Alembic head only after compatibility validation succeeds",
    )
    args = parser.parse_args()

    issues = asyncio.run(find_schema_issues())
    if issues:
        print("Legacy schema is not compatible with the Alembic baseline:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Legacy schema matches the Alembic baseline.")
    if args.stamp:
        command.stamp(Config("alembic.ini"), "head")
        print("Stamped Alembic head after successful validation.")
    else:
        print("Re-run with --stamp to record the baseline revision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
