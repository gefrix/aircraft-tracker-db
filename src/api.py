from __future__ import annotations

import time
from collections.abc import Callable

import requests

from src.base_api import BaseAircraftAPI
from src.exceptions import APIError, CountryNotFoundError, DataValidationError
from src.models import Aeroplane, Country


class NominatimOpenSkyAPI(BaseAircraftAPI):
    """Load country boundaries from Nominatim and live aircraft from OpenSky."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OPENSKY_URL = "https://opensky-network.org/api/states/all"

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        nominatim_interval: float = 1.0,
        sleep_func: Callable[[float], None] = time.sleep,
        clock_func: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the API client with injectable networking and timing dependencies."""
        if timeout <= 0 or nominatim_interval < 0:
            raise ValueError("Тайм-аут должен быть положительным, а интервал — неотрицательным")
        self._session = session or requests.Session()
        self._timeout = timeout
        self._nominatim_interval = nominatim_interval
        self._sleep = sleep_func
        self._clock = clock_func
        self._last_nominatim_request: float | None = None
        self._headers = {"User-Agent": "aircraft-tracker-db-coursework/1.0"}

    def _respect_nominatim_rate_limit(self) -> None:
        """Wait when needed so Nominatim requests respect the configured interval."""
        now = self._clock()
        if self._last_nominatim_request is not None:
            remaining = self._nominatim_interval - (now - self._last_nominatim_request)
            if remaining > 0:
                self._sleep(remaining)
        self._last_nominatim_request = self._clock()

    def get_country(self, country_name: str) -> Country:
        """Request and validate one country's Nominatim bounding box."""
        normalized_name = country_name.strip()
        if not normalized_name:
            raise ValueError("Название страны не может быть пустым")
        self._respect_nominatim_rate_limit()
        params: dict[str, str | int] = {"country": normalized_name, "format": "jsonv2", "limit": 1}
        try:
            response = self._session.get(
                self.NOMINATIM_URL,
                params=params,
                headers=self._headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            raise APIError(f"Не удалось получить координаты страны: {error}") from error
        except ValueError as error:
            raise APIError("Nominatim вернул некорректный JSON") from error

        if not isinstance(payload, list) or not payload:
            raise CountryNotFoundError(f"Страна «{normalized_name}» не найдена")
        first_result = payload[0]
        if not isinstance(first_result, dict):
            raise APIError("Nominatim вернул данные в неожиданном формате")
        bounds = first_result.get("boundingbox")
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise APIError("В ответе Nominatim отсутствует корректный boundingbox")
        try:
            return Country(normalized_name, bounds[0], bounds[1], bounds[2], bounds[3])
        except DataValidationError as error:
            raise APIError(f"Nominatim вернул некорректные координаты: {error}") from error

    def get_aeroplanes(self, country: Country) -> list[Aeroplane]:
        """Request, validate and return only airborne aircraft for a country."""
        south, north, west, east = country.bounds
        params = {"lamin": south, "lamax": north, "lomin": west, "lomax": east}
        try:
            response = self._session.get(self.OPENSKY_URL, params=params, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            raise APIError(f"Не удалось получить данные OpenSky: {error}") from error
        except ValueError as error:
            raise APIError("OpenSky вернул некорректный JSON") from error

        if not isinstance(payload, dict):
            raise APIError("OpenSky вернул данные в неожиданном формате")
        states = payload.get("states")
        if states is None:
            return []
        if not isinstance(states, list):
            raise APIError("Поле states в ответе OpenSky должно быть списком")

        aeroplanes: list[Aeroplane] = []
        for state in states:
            if not isinstance(state, list):
                continue
            try:
                aeroplane = Aeroplane.from_state_vector(state)
            except DataValidationError:
                continue
            if not aeroplane.on_ground:
                aeroplanes.append(aeroplane)
        return aeroplanes


AeroplanesAPI = NominatimOpenSkyAPI
