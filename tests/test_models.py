from __future__ import annotations

import math

import pytest

from src.exceptions import DataValidationError
from src.models import Aeroplane, Country, LoadReport


def test_country_normalizes_and_exposes_bounds() -> None:
    """Country should normalize its name and return API-order bounds."""
    country = Country(" Spain ", 36, 44, -10, 4)

    assert country.name == "Spain"
    assert country.bounds == (36.0, 44.0, -10.0, 4.0)


@pytest.mark.parametrize(
    "arguments",
    [
        ("", 36, 44, -10, 4),
        ("Spain", 45, 44, -10, 4),
        ("Spain", -91, 44, -10, 4),
        ("Spain", 36, 44, 5, 4),
        ("Spain", 36, 44, -10, 181),
    ],
)
def test_country_rejects_invalid_data(arguments: tuple[object, ...]) -> None:
    """Country validation should reject blank names and invalid coordinates."""
    with pytest.raises(DataValidationError):
        Country(*arguments)  # type: ignore[arg-type]


def test_aeroplane_from_state_vector_maps_all_required_fields(state_vector: list[object]) -> None:
    """OpenSky vector positions should map to typed model attributes."""
    aeroplane = Aeroplane.from_state_vector(state_vector)

    assert aeroplane.icao24 == "4b1812"
    assert aeroplane.callsign == "SWR438A"
    assert aeroplane.origin_country == "Switzerland"
    assert aeroplane.velocity == 189.7
    assert aeroplane.altitude == 4267.2
    assert aeroplane.longitude == -0.0168
    assert aeroplane.latitude == 51.0888
    assert not aeroplane.on_ground
    assert aeroplane.last_contact == 1766166618


def test_aeroplane_uses_fallbacks_for_optional_values(state_vector: list[object]) -> None:
    """Missing callsign, origin and barometric altitude should have safe fallbacks."""
    state_vector[1] = None
    state_vector[2] = None
    state_vector[7] = None
    state_vector[9] = None

    aeroplane = Aeroplane.from_state_vector(state_vector)

    assert aeroplane.callsign == "UNKNOWN-4B1812"
    assert aeroplane.origin_country == "Unknown"
    assert aeroplane.velocity is None
    assert aeroplane.altitude == 4282.44


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("icao24", ""),
        ("icao24", "1234567"),
        ("velocity", -1),
        ("velocity", math.inf),
        ("longitude", 181),
        ("latitude", -91),
        ("on_ground", "false"),
        ("last_contact", 1.5),
    ],
)
def test_aeroplane_rejects_invalid_data(keyword: str, value: object) -> None:
    """Aircraft validation should reject invalid identifiers and numeric fields."""
    arguments: dict[str, object] = {
        "icao24": "abc123",
        "callsign": "ABC",
        "origin_country": "France",
        "velocity": 100,
        "altitude": 1000,
        "longitude": 1,
        "latitude": 1,
        "on_ground": False,
        "last_contact": 1,
    }
    arguments[keyword] = value

    with pytest.raises(DataValidationError):
        Aeroplane(**arguments)  # type: ignore[arg-type]


def test_short_state_vector_is_rejected() -> None:
    """Incomplete OpenSky vectors should not create partial objects."""
    with pytest.raises(DataValidationError, match="17 полей"):
        Aeroplane.from_state_vector(["short"])


def test_load_report_counts_failed_countries() -> None:
    """LoadReport should derive the failed count from its error mapping."""
    report = LoadReport(10, 8, 100, {"A": "error", "B": "error"})

    assert report.failed_countries == 2
