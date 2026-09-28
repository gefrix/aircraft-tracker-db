from abc import ABC, abstractmethod

from src.models import Aeroplane, Country


class BaseAircraftAPI(ABC):
    """Define operations required from a country and aircraft API provider."""

    @abstractmethod
    def get_country(self, country_name: str) -> Country:
        """Return geographic boundaries for one country."""

    @abstractmethod
    def get_aeroplanes(self, country: Country) -> list[Aeroplane]:
        """Return airborne aircraft inside a country's rectangular boundaries."""
