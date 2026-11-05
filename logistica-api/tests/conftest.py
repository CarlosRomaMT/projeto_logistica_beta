import os

# Aponta a aplicação para o banco de testes antes de importar app.core.db.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://frota:frota@localhost:5433/frota_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import app
from scripts.reset_demo import recriar_banco


@pytest.fixture(autouse=True)
def banco_limpo():
    recriar_banco(os.environ["DATABASE_URL"])
    engine.dispose()  # descarta conexões com statements preparados contra as tabelas antigas
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def consultar():
    def _consultar(sql: str, **params):
        with engine.connect() as conn:
            return conn.execute(text(sql), params).mappings().all()
    return _consultar


@pytest.fixture
def viatura(consultar):
    """Busca a viatura pela placa, inclusive a coluna legada (que a API não expõe)."""
    def _viatura(placa: str):
        return consultar("SELECT * FROM tb_viatura WHERE placa = :placa", placa=placa)[0]
    return _viatura
