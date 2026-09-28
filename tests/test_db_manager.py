from __future__ import annotations

from unittest.mock import MagicMock, Mock

import psycopg2
import pytest

from src.db_manager import DBManager
from src.exceptions import DatabaseError


def _manager_with_rows(
    rows: list[dict[str, object]],
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> tuple[DBManager, MagicMock, MagicMock]:
    """Build a query manager whose cursor returns selected rows."""
    connection, cursor = connection_and_cursor
    cursor.fetchall.return_value = rows
    return DBManager(Mock(return_value=connection)), connection, cursor


def test_countries_and_count_uses_left_join(
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Method one should include countries with zero aircraft through LEFT JOIN."""
    rows = [{"country": "Spain", "aeroplanes_count": 2}]
    manager, connection, cursor = _manager_with_rows(rows, connection_and_cursor)

    result = manager.get_countries_and_aeroplanes_count()

    assert result == rows
    query = cursor.execute.call_args.args[0]
    assert "LEFT JOIN aeroplanes" in query
    assert "COUNT(a.icao24)" in query
    assert "GROUP BY" in query
    connection.close.assert_called_once_with()


def test_get_all_aeroplanes_returns_complete_joined_rows(
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """All-aircraft query should expose the monitored country and every stored aircraft field."""
    row = {
        "monitored_country": "Spain",
        "icao24": "abc123",
        "callsign": "ACA100",
        "origin_country": "Canada",
        "velocity": 250.0,
        "altitude": 10000.0,
        "longitude": 1.0,
        "latitude": 2.0,
        "on_ground": False,
        "last_contact": 1,
    }
    manager, _, cursor = _manager_with_rows([row], connection_and_cursor)

    assert manager.get_all_aeroplanes() == [row]
    query = cursor.execute.call_args.args[0]
    assert "INNER JOIN countries" in query
    for field in row:
        assert field in query


def test_get_avg_speed_returns_float(connection_and_cursor: tuple[MagicMock, MagicMock]) -> None:
    """Average query should use SQL AVG and normalize the scalar result to float."""
    manager, _, cursor = _manager_with_rows([{"average_speed": 245.5}], connection_and_cursor)

    assert manager.get_avg_speed() == 245.5
    assert "AVG(velocity)" in cursor.execute.call_args.args[0]


def test_get_avg_speed_handles_empty_result(connection_and_cursor: tuple[MagicMock, MagicMock]) -> None:
    """Unexpected empty aggregate result should safely return zero."""
    manager, _, _ = _manager_with_rows([], connection_and_cursor)

    assert manager.get_avg_speed() == 0.0


def test_higher_speed_query_compares_with_subquery_average(
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Above-average method should compare velocity against a nested AVG query."""
    manager, _, cursor = _manager_with_rows([], connection_and_cursor)

    assert manager.get_aeroplanes_with_higher_speed() == []
    query = cursor.execute.call_args.args[0]
    assert "a.velocity >" in query
    assert "SELECT AVG(velocity)" in query
    assert "ORDER BY a.velocity DESC" in query


def test_keyword_search_is_parameterized_and_case_insensitive(
    connection_and_cursor: tuple[MagicMock, MagicMock],
) -> None:
    """Callsign search should use ILIKE and a parameter rather than SQL interpolation."""
    manager, _, cursor = _manager_with_rows([], connection_and_cursor)

    assert manager.get_aeroplanes_with_keyword(" ACA ") == []
    query, params = cursor.execute.call_args.args
    assert "ILIKE %s" in query
    assert params == ("%ACA%",)
    with pytest.raises(ValueError, match="пустым"):
        manager.get_aeroplanes_with_keyword(" ")


def test_query_failure_is_wrapped(connection_and_cursor: tuple[MagicMock, MagicMock]) -> None:
    """Driver errors should become DatabaseError and still close the connection."""
    connection, cursor = connection_and_cursor
    cursor.execute.side_effect = psycopg2.DatabaseError("bad query")
    manager = DBManager(Mock(return_value=connection))

    with pytest.raises(DatabaseError, match="запрос"):
        manager.get_all_aeroplanes()

    connection.close.assert_called_once_with()
