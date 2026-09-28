from __future__ import annotations

from unittest.mock import patch

import psycopg2
import pytest

from src.config import DatabaseConfig
from src.exceptions import DatabaseError


def test_config_loads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """PostgreSQL settings should be read and typed from environment variables."""
    monkeypatch.setenv("PGHOST", "db.example")
    monkeypatch.setenv("PGPORT", "5433")
    monkeypatch.setenv("PGDATABASE", "planes")
    monkeypatch.setenv("PGUSER", "pilot")
    monkeypatch.setenv("PGPASSWORD", "secret")

    config = DatabaseConfig.from_environment()

    assert config == DatabaseConfig("db.example", 5433, "planes", "pilot", "secret")


@pytest.mark.parametrize("port", ["bad", "0", "70000"])
def test_config_rejects_invalid_port(monkeypatch: pytest.MonkeyPatch, port: str) -> None:
    """PGPORT should be a valid TCP port number."""
    monkeypatch.setenv("PGPORT", port)

    with pytest.raises(DatabaseError, match="PGPORT"):
        DatabaseConfig.from_environment()


def test_connect_passes_all_parameters() -> None:
    """DatabaseConfig.connect should delegate to psycopg2 with named arguments."""
    config = DatabaseConfig("localhost", 5432, "planes", "pilot", "secret")

    with patch("src.config.psycopg2.connect") as connect:
        result = config.connect()

    assert result is connect.return_value
    connect.assert_called_once_with(
        host="localhost",
        port=5432,
        dbname="planes",
        user="pilot",
        password="secret",
    )


def test_connect_wraps_psycopg2_error() -> None:
    """Connection failures should be exposed as DatabaseError."""
    config = DatabaseConfig("localhost", 5432, "planes", "pilot", "secret")

    with patch("src.config.psycopg2.connect", side_effect=psycopg2.OperationalError("down")):
        with pytest.raises(DatabaseError, match="подключиться"):
            config.connect()
