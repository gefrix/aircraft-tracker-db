from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PostgreSQLConnection

from src.exceptions import DatabaseError


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Store PostgreSQL connection parameters loaded from the environment."""

    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_environment(cls) -> DatabaseConfig:
        """Build configuration from a local .env file and process environment."""
        load_dotenv()
        try:
            port = int(os.getenv("PGPORT", "5432"))
        except ValueError as error:
            raise DatabaseError("PGPORT должен быть целым числом") from error
        if not 1 <= port <= 65535:
            raise DatabaseError("PGPORT должен находиться в диапазоне от 1 до 65535")
        values = {
            "host": os.getenv("PGHOST", "localhost").strip(),
            "database": os.getenv("PGDATABASE", "aircraft_tracker").strip(),
            "user": os.getenv("PGUSER", "tracker").strip(),
            "password": os.getenv("PGPASSWORD", "tracker_password"),
        }
        if not all(values.values()):
            raise DatabaseError("Параметры подключения к PostgreSQL не могут быть пустыми")
        return cls(port=port, **values)

    def connect(self) -> PostgreSQLConnection:
        """Open and return a new psycopg2 connection."""
        try:
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
            )
        except psycopg2.Error as error:
            raise DatabaseError(f"Не удалось подключиться к PostgreSQL: {error}") from error
