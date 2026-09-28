from __future__ import annotations

from collections.abc import Sequence

from src.base_api import BaseAircraftAPI
from src.base_repository import BaseAircraftRepository
from src.exceptions import AircraftDatabaseError
from src.models import LoadReport

DEFAULT_COUNTRIES: tuple[str, ...] = (
    "Canada",
    "United States",
    "Brazil",
    "United Kingdom",
    "France",
    "Germany",
    "Spain",
    "Italy",
    "Japan",
    "Australia",
)


class AircraftLoader:
    """Coordinate API extraction and PostgreSQL loading without mixing responsibilities."""

    def __init__(self, api: BaseAircraftAPI, repository: BaseAircraftRepository) -> None:
        """Initialize the ETL service with API and persistence abstractions."""
        self._api = api
        self._repository = repository

    def load(self, country_names: Sequence[str] = DEFAULT_COUNTRIES) -> LoadReport:
        """Load snapshots for at least four unique countries and continue after expected failures."""
        normalized_names = tuple(dict.fromkeys(name.strip() for name in country_names if name.strip()))
        if len(normalized_names) < 4:
            raise ValueError("Для загрузки необходимо указать не менее четырех разных стран")

        loaded_countries = 0
        loaded_aeroplanes = 0
        errors: dict[str, str] = {}
        for country_name in normalized_names:
            try:
                country = self._api.get_country(country_name)
                aeroplanes = self._api.get_aeroplanes(country)
                self._repository.save_country_with_aeroplanes(country, aeroplanes)
            except AircraftDatabaseError as error:
                errors[country_name] = str(error)
                continue
            loaded_countries += 1
            loaded_aeroplanes += len(aeroplanes)

        return LoadReport(
            requested_countries=len(normalized_names),
            loaded_countries=loaded_countries,
            loaded_aeroplanes=loaded_aeroplanes,
            errors=errors,
        )
