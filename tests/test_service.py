from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.exceptions import APIError
from src.models import Aeroplane, Country
from src.service import DEFAULT_COUNTRIES, AircraftLoader


def test_default_country_set_has_ten_unique_values() -> None:
    """The default ETL set should satisfy the stricter ten-country criterion."""
    assert len(DEFAULT_COUNTRIES) == 10
    assert len(set(DEFAULT_COUNTRIES)) == 10


def test_loader_saves_every_successful_country(aeroplane: Aeroplane) -> None:
    """ETL should combine API extraction and repository loading for each country."""
    api = Mock()
    repository = Mock()
    api.get_country.side_effect = lambda name: Country(name, 1, 2, 3, 4)
    api.get_aeroplanes.return_value = [aeroplane]
    loader = AircraftLoader(api, repository)

    report = loader.load(["A", "B", "C", "D"])

    assert report.requested_countries == 4
    assert report.loaded_countries == 4
    assert report.loaded_aeroplanes == 4
    assert report.errors == {}
    assert repository.save_country_with_aeroplanes.call_count == 4


def test_loader_continues_after_expected_error(aeroplane: Aeroplane) -> None:
    """A failed API country should be reported without blocking remaining countries."""
    api = Mock()
    repository = Mock()

    def get_country(name: str) -> Country:
        if name == "B":
            raise APIError("unavailable")
        return Country(name, 1, 2, 3, 4)

    api.get_country.side_effect = get_country
    api.get_aeroplanes.return_value = [aeroplane]
    report = AircraftLoader(api, repository).load(["A", "B", "C", "D"])

    assert report.loaded_countries == 3
    assert report.failed_countries == 1
    assert report.errors == {"B": "unavailable"}


def test_loader_requires_four_unique_countries() -> None:
    """The service should enforce the assignment's minimum country count."""
    loader = AircraftLoader(Mock(), Mock())

    with pytest.raises(ValueError, match="четырех"):
        loader.load(["A", "A", "B", "C"])
