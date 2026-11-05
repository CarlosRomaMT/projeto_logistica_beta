"""Consultas de visibilidade da frota (RF02).

A lotação vem SOMENTE de tb_viatura.fk_id_opm_unidade; cd_unidade_legado não é lido aqui.
"""

from sqlalchemy import text

from app.core.constantes import STATUS_DISPONIVEL
from app.core.db import engine


def buscar_p4(login: str) -> dict | None:
    with engine.connect() as conn:
        p4 = conn.execute(
            text("""
                SELECT u.login, u.nome, o.id_opm, o.nome AS nome_opm
                FROM tb_usuario_p4 u
                JOIN tb_opm o ON o.id_opm = u.fk_id_opm
                WHERE u.login = :login
            """),
            {"login": login},
        ).mappings().first()
        return dict(p4) if p4 else None


def listar_p4() -> list[dict]:
    with engine.connect() as conn:
        linhas = conn.execute(text("""
            SELECT u.login, u.nome, o.id_opm, o.nome AS nome_opm
            FROM tb_usuario_p4 u
            JOIN tb_opm o ON o.id_opm = u.fk_id_opm
            ORDER BY o.id_opm
        """)).mappings()
        return [dict(linha) for linha in linhas]


def listar_disponiveis_para_p4(login: str) -> list[dict]:
    """Viaturas da OPM do P4 com status disponível. Sem cache: lida a cada carregamento."""
    with engine.connect() as conn:
        linhas = conn.execute(
            text("""
                SELECT v.id_viatura, v.placa, v.modelo
                FROM tb_viatura v
                JOIN tb_usuario_p4 u ON u.fk_id_opm = v.fk_id_opm_unidade
                WHERE u.login = :login
                  AND v.status_operacional = :disponivel
                ORDER BY v.placa
            """),
            {"login": login, "disponivel": STATUS_DISPONIVEL},
        ).mappings()
        return [dict(linha) for linha in linhas]
