from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.exceptions import DatabaseError
from src.repository import ConnectionFactory


class DBManager:
    """Execute the five read queries required by the coursework."""

    COUNTRIES_AND_COUNT_SQL = """
        SELECT c.name AS country, COUNT(a.icao24)::INTEGER AS aeroplanes_count
        FROM countries AS c
        LEFT JOIN aeroplanes AS a ON a.country_id = c.id
        GROUP BY c.id, c.name
        ORDER BY aeroplanes_count DESC, c.name ASC
    """
    ALL_AEROPLANES_SQL = """
        SELECT c.name AS monitored_country, a.icao24, a.callsign, a.origin_country,
               a.velocity, a.altitude, a.longitude, a.latitude, a.on_ground, a.last_contact
        FROM aeroplanes AS a
        INNER JOIN countries AS c ON c.id = a.country_id
        ORDER BY c.name ASC, a.callsign ASC
    """
    AVG_SPEED_SQL = """
        SELECT COALESCE(AVG(velocity), 0)::DOUBLE PRECISION AS average_speed
        FROM aeroplanes
        WHERE velocity IS NOT NULL
    """
    HIGHER_SPEED_SQL = """
        SELECT c.name AS monitored_country, a.icao24, a.callsign, a.origin_country,
               a.velocity, a.altitude, a.longitude, a.latitude, a.on_ground, a.last_contact
        FROM aeroplanes AS a
        INNER JOIN countries AS c ON c.id = a.country_id
        WHERE a.velocity > (
            SELECT AVG(velocity) FROM aeroplanes WHERE velocity IS NOT NULL
        )
        ORDER BY a.velocity DESC, a.callsign ASC
    """
    KEYWORD_SQL = """
        SELECT c.name AS monitored_country, a.icao24, a.callsign, a.origin_country,
               a.velocity, a.altitude, a.longitude, a.latitude, a.on_ground, a.last_contact
        FROM aeroplanes AS a
        INNER JOIN countries AS c ON c.id = a.country_id
        WHERE a.callsign ILIKE %s
        ORDER BY a.callsign ASC
    """

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        """Initialize the query manager with an injectable connection factory."""
        self._connection_factory = connection_factory

    def _fetch_all(self, query: str, params: Sequence[object] | None = None) -> list[dict[str, Any]]:
        """Execute a SELECT query and return all rows as plain dictionaries."""
        connection = self._connection_factory()
        try:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as error:
            raise DatabaseError(f"Не удалось выполнить запрос к PostgreSQL: {error}") from error
        finally:
            connection.close()

    def get_countries_and_aeroplanes_count(self) -> list[dict[str, Any]]:
        """Return every monitored country with its aircraft count using LEFT JOIN."""
        return self._fetch_all(self.COUNTRIES_AND_COUNT_SQL)

    def get_all_aeroplanes(self) -> list[dict[str, Any]]:
        """Return complete aircraft information together with monitored country names."""
        return self._fetch_all(self.ALL_AEROPLANES_SQL)

    def get_avg_speed(self) -> float:
        """Return the average speed over aircraft with a known velocity."""
        rows = self._fetch_all(self.AVG_SPEED_SQL)
        return float(rows[0]["average_speed"]) if rows else 0.0

    def get_aeroplanes_with_higher_speed(self) -> list[dict[str, Any]]:
        """Return aircraft whose velocity is greater than the database average."""
        return self._fetch_all(self.HIGHER_SPEED_SQL)

    def get_aeroplanes_with_keyword(self, keyword: str) -> list[dict[str, Any]]:
        """Return aircraft whose callsign contains a case-insensitive keyword."""
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise ValueError("Ключевое слово не может быть пустым")
        return self._fetch_all(self.KEYWORD_SQL, (f"%{normalized_keyword}%",))
