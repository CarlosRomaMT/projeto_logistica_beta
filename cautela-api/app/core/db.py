import os

from sqlalchemy import create_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://frota:frota@localhost:5433/frota"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
