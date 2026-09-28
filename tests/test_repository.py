from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import psycopg2
import pytest

from src.base_repository import BaseAircraftRepository
from src.exceptions import DatabaseError
from src.models import Aeroplane, Country
from src.repository import PostgresRepository


def test_repository_implements_abstract_interface() -> None:
    """PostgreSQL repository should satisfy the ETL persistence abstraction."""
    assert issubclass(PostgresRepository, BaseAircraftRepository)
    with pytest.raises(TypeError):
        BaseAircraftRepository()  # type: ignore[abstract]


def test_create_tables_executes_complete_schema(
    tmp_path: Path,
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Repository should execute schema.sql and commit the transaction."""
    connection, cursor = connection_and_cursor
    schema_path = tmp_path / "schema.sql"
    schema = "CREATE TABLE countries (); CREATE TABLE aeroplanes ();"
    schema_path.write_text(schema, encoding="utf-8")
    repository = PostgresRepository(Mock(return_value=connection), schema_path)

    repository.create_tables()

    cursor.execute.assert_called_once_with(schema)
    connection.commit.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_create_tables_reports_missing_schema(
    tmp_path: Path,
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """A missing schema file should become a DatabaseError."""
    connection, _ = connection_and_cursor
    repository = PostgresRepository(Mock(return_value=connection), tmp_path / "missing.sql")

    with pytest.raises(DatabaseError, match="SQL-схему"):
        repository.create_tables()


def test_save_country_and_aircraft_is_atomic(
    country: Country,
    aeroplane: Aeroplane,
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Country upsert, snapshot cleanup and aircraft inserts should share one transaction."""
    connection, cursor = connection_and_cursor
    cursor.fetchone.return_value = (7,)
    repository = PostgresRepository(Mock(return_value=connection))

    repository.save_country_with_aeroplanes(country, [aeroplane])

    first_query, first_params = cursor.execute.call_args_list[0].args
    assert "ON CONFLICT (name)" in first_query
    assert first_params == ("Spain", 36.0, 44.0, -10.0, 4.0)
    cursor.execute.assert_any_call("DELETE FROM aeroplanes WHERE country_id = %s", (7,))
    inserted_values = cursor.executemany.call_args.args[1]
    assert inserted_values == [
        (7, "4b1812", "SWR438A", "Switzerland", 189.7, 4267.2, -0.0168, 51.0888, False, 1766166618)
    ]
    connection.commit.assert_called_once_with()


def test_save_requires_returned_country_id(
    country: Country,
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """An absent RETURNING id result should roll back rather than writing orphan aircraft."""
    connection, cursor = connection_and_cursor
    cursor.fetchone.return_value = None
    repository = PostgresRepository(Mock(return_value=connection))

    with pytest.raises(DatabaseError, match="идентификатор"):
        repository.save_country_with_aeroplanes(country, [])

    connection.rollback.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_psycopg2_failure_rolls_back(
    country: Country,
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Database driver failures should roll back and become DatabaseError."""
    connection, cursor = connection_and_cursor
    cursor.execute.side_effect = psycopg2.DatabaseError("broken")
    repository = PostgresRepository(Mock(return_value=connection))

    with pytest.raises(DatabaseError, match="сохранить"):
        repository.save_country_with_aeroplanes(country, [])

    connection.rollback.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_schema_defines_required_tables_and_constraints() -> None:
    """Checked-in schema should contain both tables, FK, indexes and velocity validation."""
    schema = (Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS countries" in schema
    assert "CREATE TABLE IF NOT EXISTS aeroplanes" in schema
    assert "REFERENCES countries(id) ON DELETE CASCADE" in schema
    assert "PRIMARY KEY (country_id, icao24)" in schema
    assert "non_negative_velocity" in schema
    assert schema.count("CREATE INDEX") == 3
