from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeAlias

import psycopg2
from psycopg2.extensions import connection as PostgreSQLConnection

from src.base_repository import BaseAircraftRepository
from src.exceptions import DatabaseError
from src.models import Aeroplane, Country

ConnectionFactory: TypeAlias = Callable[[], PostgreSQLConnection]


class PostgresRepository(BaseAircraftRepository):
    """Create tables and persist countries with their current aircraft states."""

    UPSERT_COUNTRY_SQL = """
        INSERT INTO countries (
            name, south_latitude, north_latitude, west_longitude, east_longitude, updated_at
        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (name) DO UPDATE SET
            south_latitude = EXCLUDED.south_latitude,
            north_latitude = EXCLUDED.north_latitude,
            west_longitude = EXCLUDED.west_longitude,
            east_longitude = EXCLUDED.east_longitude,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """
    INSERT_AEROPLANE_SQL = """
        INSERT INTO aeroplanes (
            country_id, icao24, callsign, origin_country, velocity, altitude,
            longitude, latitude, on_ground, last_contact, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (country_id, icao24) DO UPDATE SET
            callsign = EXCLUDED.callsign,
            origin_country = EXCLUDED.origin_country,
            velocity = EXCLUDED.velocity,
            altitude = EXCLUDED.altitude,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            on_ground = EXCLUDED.on_ground,
            last_contact = EXCLUDED.last_contact,
            updated_at = CURRENT_TIMESTAMP
    """

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        schema_path: str | Path | None = None,
    ) -> None:
        """Initialize the repository with a connection factory and SQL schema path."""
        self._connection_factory = connection_factory
        self._schema_path = (
            Path(schema_path) if schema_path else Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
        )

    def create_tables(self) -> None:
        """Create all required PostgreSQL tables and indexes from schema.sql."""
        try:
            schema = self._schema_path.read_text(encoding="utf-8")
        except OSError as error:
            raise DatabaseError(f"Не удалось прочитать SQL-схему: {error}") from error
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(schema)
            connection.commit()
        except psycopg2.Error as error:
            connection.rollback()
            raise DatabaseError(f"Не удалось создать таблицы: {error}") from error
        finally:
            connection.close()

    def save_country_with_aeroplanes(self, country: Country, aeroplanes: Sequence[Aeroplane]) -> None:
        """Atomically upsert a country and replace its aircraft snapshot."""
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.UPSERT_COUNTRY_SQL,
                    (country.name, *country.bounds),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError("PostgreSQL не вернул идентификатор страны")
                country_id = int(row[0])
                cursor.execute("DELETE FROM aeroplanes WHERE country_id = %s", (country_id,))
                cursor.executemany(
                    self.INSERT_AEROPLANE_SQL,
                    [self._aeroplane_values(country_id, aeroplane) for aeroplane in aeroplanes],
                )
            connection.commit()
        except psycopg2.Error as error:
            connection.rollback()
            raise DatabaseError(f"Не удалось сохранить данные в PostgreSQL: {error}") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _aeroplane_values(country_id: int, aeroplane: Aeroplane) -> tuple[object, ...]:
        """Return aircraft attributes in INSERT query order."""
        return (
            country_id,
            aeroplane.icao24,
            aeroplane.callsign,
            aeroplane.origin_country,
            aeroplane.velocity,
            aeroplane.altitude,
            aeroplane.longitude,
            aeroplane.latitude,
            aeroplane.on_ground,
            aeroplane.last_contact,
        )
