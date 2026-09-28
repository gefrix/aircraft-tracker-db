from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from src.api import AeroplanesAPI, NominatimOpenSkyAPI
from src.base_api import BaseAircraftAPI
from src.exceptions import APIError, CountryNotFoundError
from src.models import Country


def _response(payload: object) -> Mock:
    """Create a response mock returning the selected JSON payload."""
    response = Mock()
    response.json.return_value = payload
    return response


def test_api_implements_abstract_interface() -> None:
    """Concrete API client should inherit the required abstraction."""
    assert issubclass(NominatimOpenSkyAPI, BaseAircraftAPI)
    assert AeroplanesAPI is NominatimOpenSkyAPI
    with pytest.raises(TypeError):
        BaseAircraftAPI()  # type: ignore[abstract]


def test_get_country_returns_validated_bounds() -> None:
    """Nominatim response should become a Country object."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response([{"boundingbox": ["36", "44", "-10", "4"]}])
    api = NominatimOpenSkyAPI(session=session, nominatim_interval=0)

    country = api.get_country(" Spain ")

    assert country == Country("Spain", 36, 44, -10, 4)
    session.get.assert_called_once_with(
        NominatimOpenSkyAPI.NOMINATIM_URL,
        params={"country": "Spain", "format": "jsonv2", "limit": 1},
        headers={"User-Agent": "aircraft-tracker-db-coursework/1.0"},
        timeout=20.0,
    )


def test_nominatim_rate_limit_waits_between_requests() -> None:
    """Consecutive geocoding calls should respect the configured request interval."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response([{"boundingbox": ["1", "2", "3", "4"]}])
    clock = Mock(side_effect=[0.0, 0.0, 0.25, 1.0])
    sleep = Mock()
    api = NominatimOpenSkyAPI(
        session=session,
        nominatim_interval=1.0,
        clock_func=clock,
        sleep_func=sleep,
    )

    api.get_country("A")
    api.get_country("B")

    sleep.assert_called_once_with(0.75)


def test_get_aeroplanes_returns_only_airborne_valid_states(
    country: Country,
    state_vector: list[object],
) -> None:
    """OpenSky parser should skip ground, malformed and structurally invalid states."""
    on_ground = list(state_vector)
    on_ground[0] = "abc123"
    on_ground[8] = True
    invalid = list(state_vector)
    invalid[0] = "too-long-id"
    session = Mock(spec=requests.Session)
    session.get.return_value = _response({"states": [state_vector, on_ground, invalid, "bad"]})
    api = NominatimOpenSkyAPI(session=session, nominatim_interval=0)

    result = api.get_aeroplanes(country)

    assert [item.icao24 for item in result] == ["4b1812"]
    assert session.get.call_args.kwargs["params"] == {
        "lamin": 36.0,
        "lamax": 44.0,
        "lomin": -10.0,
        "lomax": 4.0,
    }


def test_null_states_returns_empty_list(country: Country) -> None:
    """OpenSky can legitimately return null when no state vector is available."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response({"states": None})

    assert NominatimOpenSkyAPI(session=session).get_aeroplanes(country) == []


def test_country_not_found_is_reported() -> None:
    """An empty Nominatim result should become a domain-specific exception."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response([])

    with pytest.raises(CountryNotFoundError, match="не найдена"):
        NominatimOpenSkyAPI(session=session).get_country("Nowhere")


@pytest.mark.parametrize("payload", [{}, ["bad"], [{"boundingbox": [1, 2]}]])
def test_invalid_nominatim_payload_is_reported(payload: object) -> None:
    """Unexpected geocoder JSON structures should not leak low-level errors."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response(payload)

    with pytest.raises(APIError):
        NominatimOpenSkyAPI(session=session).get_country("Spain")


def test_network_error_is_wrapped() -> None:
    """Requests failures should be converted to an APIError."""
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("slow")

    with pytest.raises(APIError, match="координаты"):
        NominatimOpenSkyAPI(session=session).get_country("Spain")


def test_invalid_opensky_payload_is_reported(country: Country) -> None:
    """Unexpected OpenSky payloads should be rejected explicitly."""
    session = Mock(spec=requests.Session)
    session.get.return_value = _response({"states": "bad"})

    with pytest.raises(APIError, match="states"):
        NominatimOpenSkyAPI(session=session).get_aeroplanes(country)


def test_invalid_constructor_and_country_values_are_rejected() -> None:
    """Client configuration and country name must be valid before networking."""
    with pytest.raises(ValueError, match="Тайм-аут"):
        NominatimOpenSkyAPI(timeout=0)
    with pytest.raises(ValueError, match="Название"):
        NominatimOpenSkyAPI().get_country(" ")
