from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from src.api import NominatimOpenSkyAPI
from src.config import DatabaseConfig
from src.db_manager import DBManager
from src.exceptions import AircraftDatabaseError
from src.repository import PostgresRepository
from src.service import DEFAULT_COUNTRIES, AircraftLoader

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def _format_rows(rows: Iterable[Mapping[str, Any]], limit: int | None = None) -> str:
    """Format database rows into compact human-readable console lines."""
    items = list(rows)
    if not items:
        return "Данные не найдены."
    shown = items if limit is None else items[:limit]
    lines = [" | ".join(f"{key}: {value}" for key, value in row.items()) for row in shown]
    if limit is not None and len(items) > limit:
        lines.append(f"… и еще {len(items) - limit}")
    return "\n".join(lines)


def user_interaction(
    loader: AircraftLoader | None = None,
    repository: PostgresRepository | None = None,
    manager: DBManager | None = None,
    input_func: InputFunction = input,
    output_func: OutputFunction = print,
) -> None:
    """Create tables, load ten countries and demonstrate every DBManager query."""
    if loader is None or repository is None or manager is None:
        config = DatabaseConfig.from_environment()
        repository = PostgresRepository(config.connect)
        loader = AircraftLoader(NominatimOpenSkyAPI(), repository)
        manager = DBManager(config.connect)

    try:
        repository.create_tables()
        report = loader.load(DEFAULT_COUNTRIES)
        output_func(
            f"Загружено стран: {report.loaded_countries}/{report.requested_countries}; "
            f"самолетов: {report.loaded_aeroplanes}."
        )
        for country, error in report.errors.items():
            output_func(f"Не удалось загрузить {country}: {error}")

        output_func("\nСтраны и количество самолетов:")
        output_func(_format_rows(manager.get_countries_and_aeroplanes_count()))

        all_aeroplanes = manager.get_all_aeroplanes()
        output_func(f"\nВсего записей о самолетах: {len(all_aeroplanes)}")
        output_func(_format_rows(all_aeroplanes, limit=20))

        output_func(f"\nСредняя скорость: {manager.get_avg_speed():.2f} м/с")
        output_func("\nСамолеты со скоростью выше средней:")
        output_func(_format_rows(manager.get_aeroplanes_with_higher_speed(), limit=20))

        keyword = input_func("\nВведите символы для поиска в позывном (например ACA): ").strip()
        output_func("\nРезультаты поиска:")
        output_func(_format_rows(manager.get_aeroplanes_with_keyword(keyword), limit=20))
    except (AircraftDatabaseError, ValueError) as error:
        output_func(f"Ошибка: {error}")
