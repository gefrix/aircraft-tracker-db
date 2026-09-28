class AircraftDatabaseError(Exception):
    """Base exception for expected application failures."""


class APIError(AircraftDatabaseError):
    """Report a network or external API response failure."""


class CountryNotFoundError(APIError):
    """Report that Nominatim could not find a requested country."""


class DataValidationError(AircraftDatabaseError, ValueError):
    """Report invalid country or aircraft data."""


class DatabaseError(AircraftDatabaseError):
    """Report a PostgreSQL connection or query failure."""
