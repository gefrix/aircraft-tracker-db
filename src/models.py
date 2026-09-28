from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Self

from src.exceptions import DataValidationError


def _validated_number(value: object, field: str, *, minimum: float | None = None) -> float:
    """Convert a supported value to a finite float and validate its lower bound."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise DataValidationError(f"{field} должно быть числом")
    try:
        normalized = float(value)
    except ValueError as error:
        raise DataValidationError(f"{field} должно быть числом") from error
    if not math.isfinite(normalized):
        raise DataValidationError(f"{field} должно быть конечным числом")
    if minimum is not None and normalized < minimum:
        raise DataValidationError(f"{field} не может быть меньше {minimum:g}")
    return normalized


def _optional_number(value: object | None, field: str, *, minimum: float | None = None) -> float | None:
    """Validate an optional numeric API field."""
    return None if value is None else _validated_number(value, field, minimum=minimum)


@dataclass(frozen=True, slots=True)
class Country:
    """Represent a country and its rectangular geographic boundaries."""

    name: str
    south_latitude: float
    north_latitude: float
    west_longitude: float
    east_longitude: float

    def __post_init__(self) -> None:
        """Normalize and validate country data after dataclass initialization."""
        normalized_name = self.name.strip() if isinstance(self.name, str) else ""
        if not normalized_name:
            raise DataValidationError("Название страны не может быть пустым")
        object.__setattr__(self, "name", normalized_name)

        south = _validated_number(self.south_latitude, "Южная широта")
        north = _validated_number(self.north_latitude, "Северная широта")
        west = _validated_number(self.west_longitude, "Западная долгота")
        east = _validated_number(self.east_longitude, "Восточная долгота")
        if not -90 <= south <= north <= 90:
            raise DataValidationError("Границы широты указаны некорректно")
        if not -180 <= west <= east <= 180:
            raise DataValidationError("Границы долготы указаны некорректно")
        object.__setattr__(self, "south_latitude", south)
        object.__setattr__(self, "north_latitude", north)
        object.__setattr__(self, "west_longitude", west)
        object.__setattr__(self, "east_longitude", east)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return bounds in the order expected by the OpenSky API."""
        return self.south_latitude, self.north_latitude, self.west_longitude, self.east_longitude


@dataclass(frozen=True, slots=True)
class Aeroplane:
    """Represent one validated OpenSky aircraft state."""

    icao24: str
    callsign: str
    origin_country: str
    velocity: float | None
    altitude: float | None
    longitude: float | None
    latitude: float | None
    on_ground: bool
    last_contact: int | None

    def __post_init__(self) -> None:
        """Normalize and validate aircraft data after dataclass initialization."""
        icao24 = self.icao24.strip().lower() if isinstance(self.icao24, str) else ""
        if not icao24 or len(icao24) > 6:
            raise DataValidationError("ICAO24 должен содержать от 1 до 6 символов")
        object.__setattr__(self, "icao24", icao24)

        callsign = self.callsign.strip() if isinstance(self.callsign, str) else ""
        origin_country = self.origin_country.strip() if isinstance(self.origin_country, str) else ""
        object.__setattr__(self, "callsign", callsign or f"UNKNOWN-{icao24.upper()}")
        object.__setattr__(self, "origin_country", origin_country or "Unknown")
        object.__setattr__(self, "velocity", _optional_number(self.velocity, "Скорость", minimum=0.0))
        object.__setattr__(self, "altitude", _optional_number(self.altitude, "Высота"))
        object.__setattr__(self, "longitude", self._coordinate(self.longitude, "Долгота", -180.0, 180.0))
        object.__setattr__(self, "latitude", self._coordinate(self.latitude, "Широта", -90.0, 90.0))
        if not isinstance(self.on_ground, bool):
            raise DataValidationError("Признак нахождения на земле должен быть логическим")
        if self.last_contact is not None and (
            isinstance(self.last_contact, bool) or not isinstance(self.last_contact, int)
        ):
            raise DataValidationError("Время последнего контакта должно быть целым числом")

    @staticmethod
    def _coordinate(value: object | None, field: str, minimum: float, maximum: float) -> float | None:
        """Validate an optional longitude or latitude value."""
        normalized = _optional_number(value, field)
        if normalized is not None and not minimum <= normalized <= maximum:
            raise DataValidationError(f"{field} выходит за допустимый диапазон")
        return normalized

    @classmethod
    def from_state_vector(cls, state: list[Any]) -> Self:
        """Create an aircraft from one OpenSky state vector."""
        if len(state) < 17:
            raise DataValidationError("Вектор состояния OpenSky должен содержать не менее 17 полей")
        barometric_altitude = state[7]
        geometric_altitude = state[13]
        altitude = barometric_altitude if barometric_altitude is not None else geometric_altitude
        return cls(
            icao24=str(state[0]) if state[0] is not None else "",
            callsign=str(state[1]) if state[1] is not None else "",
            origin_country=str(state[2]) if state[2] is not None else "",
            velocity=state[9],
            altitude=altitude,
            longitude=state[5],
            latitude=state[6],
            on_ground=bool(state[8]),
            last_contact=state[4] if isinstance(state[4], int) and not isinstance(state[4], bool) else None,
        )


@dataclass(frozen=True, slots=True)
class LoadReport:
    """Summarize an ETL run across the configured countries."""

    requested_countries: int
    loaded_countries: int
    loaded_aeroplanes: int
    errors: dict[str, str]

    @property
    def failed_countries(self) -> int:
        """Return the number of countries that could not be loaded."""
        return len(self.errors)
