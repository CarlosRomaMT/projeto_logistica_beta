"""Leitura do cadastro antigo, só para diagnóstico/demonstração do problema.

Fica fora da listagem oficial de viaturas, que não expõe a coluna legada (RNF02).
"""

from sqlalchemy import text

from app.core.db import engine


def listar_legado_das_viaturas() -> list[dict]:
    with engine.connect() as conn:
        linhas = conn.execute(text("""
            SELECT v.id_viatura, v.cd_unidade_legado, u.ds_unidade AS ds_unidade_legado,
                   d.situacao AS situacao_de_para, d.fk_id_opm AS id_opm_de_para,
                   o.nome AS nome_opm_de_para, d.score
            FROM tb_viatura v
            LEFT JOIN tb_unidade_legado u ON u.cd_unidade = v.cd_unidade_legado
            LEFT JOIN tb_de_para_unidade d ON d.cd_unidade_legado = v.cd_unidade_legado
            LEFT JOIN tb_opm o ON o.id_opm = d.fk_id_opm
            ORDER BY v.id_viatura
        """)).mappings()
        return [dict(linha) for linha in linhas]
