import os
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://frota:frota@localhost:5433/frota_test"
)

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import app

DIR_SQL = Path(os.environ.get("DB_SQL_DIR", Path(__file__).resolve().parents[2] / "db"))


@pytest.fixture(autouse=True)
def banco_limpo():
    with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as conn:
        for nome in ("01_schema.sql", "02_seed.sql"):
            conn.execute((DIR_SQL / nome).read_text(encoding="utf-8"))
    engine.dispose()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def executar():
    def _executar(sql: str, **params):
        with engine.begin() as conn:
            conn.execute(text(sql), params)
    return _executar
