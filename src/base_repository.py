from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.models import Aeroplane, Country


class BaseAircraftRepository(ABC):
    """Define the persistence operation required by the ETL service."""

    @abstractmethod
    def save_country_with_aeroplanes(self, country: Country, aeroplanes: Sequence[Aeroplane]) -> None:
        """Persist a country together with its current aircraft snapshot."""
