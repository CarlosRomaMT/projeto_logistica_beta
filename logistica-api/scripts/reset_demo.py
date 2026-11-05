"""Recria o schema e os dados fictícios (volta ao estado "antes da correção").

Uso: python -m scripts.reset_demo
"""

import os
from pathlib import Path

import psycopg

DIR_SQL = Path(os.environ.get("DB_SQL_DIR", Path(__file__).resolve().parents[2] / "db"))
ARQUIVOS = ("01_schema.sql", "02_seed.sql")


def recriar_banco(database_url: str):
    with psycopg.connect(database_url.replace("+psycopg", "")) as conn:
        for nome in ARQUIVOS:
            conn.execute((DIR_SQL / nome).read_text(encoding="utf-8"))


if __name__ == "__main__":
    from app.core.db import DATABASE_URL, engine
    from app.services.de_para import sincronizar_de_para

    recriar_banco(DATABASE_URL)
    # Mesmo estado da subida da API: sugestões do de-para prontas para o revisor.
    with engine.begin() as conn:
        criadas = sincronizar_de_para(conn)
    print(f"Banco recriado com os dados fictícios. De-para sugerido para {criadas} unidade(s) antiga(s).")
