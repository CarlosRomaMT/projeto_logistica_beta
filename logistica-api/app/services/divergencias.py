"""Correção das viaturas cuja coluna nova diverge do legado (o bug original).

Divergência = a coluna nova aponta para uma OPM e o legado, pelo de-para confirmado, para outra.
Só vale para viaturas NUNCA movimentadas pelo sistema novo: depois da implantação o legado fica
congelado (RF01), então uma viatura movimentada sempre "divergiria" e não pode ser revertida.

Nada é aplicado sem decisão humana. A aplicação passa pelo serviço de movimentação
(RF01/RF03, histórico) e um lote é tudo ou nada (RNF01).
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import ID_OPM_CONTINGENCIA, STATUS_BAIXADA, STATUS_QUE_IMPEDEM_NA_IMPLANTACAO
from app.core.db import engine
from app.errors import PropostaInvalida
from app.services.de_para import mapa_de_para, resolver_opm
from app.services.movimentacao import mover_viatura_na_transacao

TIPO_MOVIMENTACAO = "CORRECAO_CARGA"


def listar_divergencias(conn: Connection, mapa: dict) -> list[dict]:
    linhas = conn.execute(
        text("""
            SELECT v.id_viatura, v.placa, v.cd_unidade_legado, v.fk_id_opm_unidade
            FROM tb_viatura v
            WHERE v.fk_id_opm_unidade IS NOT NULL AND v.fk_id_opm_unidade <> :contingencia
              AND v.status_operacional <> :baixada
              AND NOT EXISTS (SELECT 1 FROM tb_historico_movimentacao h
                              WHERE h.id_viatura = v.id_viatura)
            ORDER BY v.id_viatura
        """),
        {"contingencia": ID_OPM_CONTINGENCIA, "baixada": STATUS_BAIXADA},
    ).mappings()
    divergentes = []
    for v in linhas:
        id_opm, _ = resolver_opm(v["cd_unidade_legado"], mapa)
        if id_opm is not None and id_opm != v["fk_id_opm_unidade"]:
            divergentes.append({**v, "id_opm_proposta": id_opm})
    return divergentes


def gerar_propostas(conn: Connection) -> int:
    """Cria propostas para as divergências ainda sem proposta aberta nem rejeição igual."""
    criadas = 0
    for d in listar_divergencias(conn, mapa_de_para(conn)):
        ja_tratada = conn.execute(
            text("""
                SELECT 1 FROM tb_correcao_divergencia
                WHERE id_viatura = :viatura
                  AND (situacao = 'PROPOSTA'
                       OR (situacao = 'REJEITADA' AND id_opm_atual = :atual
                           AND id_opm_proposta = :proposta))
            """),
            {"viatura": d["id_viatura"], "atual": d["fk_id_opm_unidade"],
             "proposta": d["id_opm_proposta"]},
        ).scalar()
        if ja_tratada:
            continue
        conn.execute(
            text("""
                INSERT INTO tb_correcao_divergencia (id_viatura, id_opm_atual, id_opm_proposta)
                VALUES (:viatura, :atual, :proposta)
            """),
            {"viatura": d["id_viatura"], "atual": d["fk_id_opm_unidade"],
             "proposta": d["id_opm_proposta"]},
        )
        criadas += 1
    return criadas


def procurar_divergencias() -> int:
    with engine.begin() as conn:
        return gerar_propostas(conn)


def listar_propostas() -> list[dict]:
    with engine.connect() as conn:
        linhas = conn.execute(text("""
            SELECT c.id, c.id_viatura, v.placa, v.modelo, v.status_operacional,
                   v.cd_unidade_legado, u.ds_unidade AS ds_unidade_legado,
                   c.id_opm_atual, oa.nome AS nome_opm_atual,
                   c.id_opm_proposta, op.nome AS nome_opm_proposta,
                   c.situacao, c.decidido_por, c.dt_decisao, c.dt_criacao
            FROM tb_correcao_divergencia c
            JOIN tb_viatura v ON v.id_viatura = c.id_viatura
            LEFT JOIN tb_unidade_legado u ON u.cd_unidade = v.cd_unidade_legado
            JOIN tb_opm oa ON oa.id_opm = c.id_opm_atual
            JOIN tb_opm op ON op.id_opm = c.id_opm_proposta
            ORDER BY (c.situacao <> 'PROPOSTA'), c.dt_decisao DESC NULLS FIRST, v.placa
        """)).mappings()
        return [
            {**linha, "bloqueio": linha["status_operacional"]
             if linha["situacao"] == "PROPOSTA"
             and linha["status_operacional"] in STATUS_QUE_IMPEDEM_NA_IMPLANTACAO else None}
            for linha in linhas
        ]


def _proposta_em_aberto(conn: Connection, id_proposta: int) -> dict:
    proposta = conn.execute(
        text("SELECT * FROM tb_correcao_divergencia WHERE id = :id FOR UPDATE"),
        {"id": id_proposta},
    ).mappings().first()
    if proposta is None or proposta["situacao"] != "PROPOSTA":
        raise PropostaInvalida(f"Proposta {id_proposta} não existe ou já foi decidida.")
    return dict(proposta)


def _decidir(conn: Connection, id_proposta: int, situacao: str, usuario: str):
    conn.execute(
        text("""
            UPDATE tb_correcao_divergencia
            SET situacao = :situacao, decidido_por = :usuario, dt_decisao = now()
            WHERE id = :id
        """),
        {"situacao": situacao, "usuario": usuario, "id": id_proposta},
    )


def aplicar_propostas(ids: list[int], usuario: str) -> list[str]:
    """Aplica as propostas aprovadas. Tudo ou nada: qualquer erro desfaz o lote inteiro."""
    aplicadas = []
    with engine.begin() as conn:
        for id_proposta in ids:
            proposta = _proposta_em_aberto(conn, id_proposta)
            atual = conn.execute(
                text("SELECT placa, fk_id_opm_unidade FROM tb_viatura WHERE id_viatura = :id"),
                {"id": proposta["id_viatura"]},
            ).mappings().first()
            if atual["fk_id_opm_unidade"] != proposta["id_opm_atual"]:
                raise PropostaInvalida(
                    f"A viatura {atual['placa']} mudou de OPM depois da proposta; procure as divergências de novo."
                )
            viatura = mover_viatura_na_transacao(
                conn, proposta["id_viatura"], proposta["id_opm_proposta"], usuario, TIPO_MOVIMENTACAO,
                implantacao=True,
            )
            _decidir(conn, id_proposta, "APLICADA", usuario)
            aplicadas.append(viatura["placa"])
    return aplicadas


def rejeitar_propostas(ids: list[int], usuario: str) -> int:
    with engine.begin() as conn:
        for id_proposta in ids:
            _proposta_em_aberto(conn, id_proposta)
            _decidir(conn, id_proposta, "REJEITADA", usuario)
    return len(ids)
