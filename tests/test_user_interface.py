from __future__ import annotations

from unittest.mock import Mock

from src.exceptions import DatabaseError
from src.models import LoadReport
from src.user_interface import _format_rows, user_interaction


def test_format_rows_handles_empty_and_limit() -> None:
    """Console formatter should be readable for empty and truncated datasets."""
    assert _format_rows([]) == "Данные не найдены."
    result = _format_rows([{"a": 1}, {"a": 2}], limit=1)
    assert result == "a: 1\n… и еще 1"


def test_user_interaction_uses_all_required_queries() -> None:
    """Console scenario should create tables, load data and call all five manager methods."""
    repository = Mock()
    loader = Mock()
    manager = Mock()
    loader.load.return_value = LoadReport(10, 9, 42, {"Japan": "timeout"})
    manager.get_countries_and_aeroplanes_count.return_value = [{"country": "Spain", "aeroplanes_count": 5}]
    manager.get_all_aeroplanes.return_value = [{"callsign": "ACA100"}]
    manager.get_avg_speed.return_value = 123.456
    manager.get_aeroplanes_with_higher_speed.return_value = [{"callsign": "FAST1"}]
    manager.get_aeroplanes_with_keyword.return_value = [{"callsign": "ACA100"}]
    output: list[str] = []

    user_interaction(
        loader=loader,
        repository=repository,
        manager=manager,
        input_func=lambda prompt: "ACA",
        output_func=output.append,
    )

    repository.create_tables.assert_called_once_with()
    loader.load.assert_called_once()
    manager.get_countries_and_aeroplanes_count.assert_called_once_with()
    manager.get_all_aeroplanes.assert_called_once_with()
    manager.get_avg_speed.assert_called_once_with()
    manager.get_aeroplanes_with_higher_speed.assert_called_once_with()
    manager.get_aeroplanes_with_keyword.assert_called_once_with("ACA")
    rendered = "\n".join(output)
    assert "Загружено стран: 9/10" in rendered
    assert "Не удалось загрузить Japan" in rendered
    assert "Средняя скорость: 123.46" in rendered


def test_user_interaction_handles_database_error() -> None:
    """Expected application errors should be displayed rather than terminating the program."""
    repository = Mock()
    repository.create_tables.side_effect = DatabaseError("database unavailable")
    output: list[str] = []

    user_interaction(
        loader=Mock(),
        repository=repository,
        manager=Mock(),
        input_func=lambda prompt: "ACA",
        output_func=output.append,
    )

    assert output == ["Ошибка: database unavailable"]
