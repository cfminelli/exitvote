"""
Shared test fixtures.

We use a temporary in-memory SQLite DB for each test session so tests
are fully isolated and never touch the real exitvote.db file.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.database import init_db, get_connection
from src.main import app


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> Path:
    """A temporary DB file shared across the test session."""
    return tmp_path_factory.mktemp("data") / "test.db"


@pytest.fixture(scope="session", autouse=True)
def setup_db(db_path: Path) -> None:
    """Initialize DB tables once for the whole test session."""
    init_db(db_path)


@pytest.fixture(scope="session")
def client(db_path: Path) -> TestClient:
    """FastAPI test client wired to the temp DB."""
    def override_get_connection() -> sqlite3.Connection:
        return get_connection(db_path)

    app.dependency_overrides[get_connection] = override_get_connection
    return TestClient(app)
