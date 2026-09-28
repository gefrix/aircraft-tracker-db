from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.models import Aeroplane, Country


@pytest.fixture
def country() -> Country:
    """Return representative country boundaries."""
    return Country("Spain", 36.0, 44.0, -10.0, 4.0)


@pytest.fixture
def state_vector() -> list[object]:
    """Return a complete airborne OpenSky state vector."""
    return [
        "4b1812",
        "SWR438A ",
        "Switzerland",
        1766166618,
        1766166618,
        -0.0168,
        51.0888,
        4267.2,
        False,
        189.7,
        129.39,
        14.63,
        None,
        4282.44,
        "2061",
        False,
        0,
    ]


@pytest.fixture
def aeroplane(state_vector: list[object]) -> Aeroplane:
    """Return a validated aircraft object."""
    return Aeroplane.from_state_vector(state_vector)


@pytest.fixture
def connection_and_cursor() -> tuple[MagicMock, MagicMock]:
    """Return a psycopg2-like connection and context-managed cursor mock."""
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    return connection, cursor
