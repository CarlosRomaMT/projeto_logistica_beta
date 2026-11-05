"""Ponto ÚNICO de escrita da lotação de viaturas (RF01, RF03, RNF01).

Toda criação ou movimentação passa por aqui. Cada operação roda numa transação
explícita: se qualquer passo falhar (viatura, histórico ou notificação), nada é gravado.
A coluna cd_unidade_legado nunca é escrita.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.core.config import (
    ID_OPM_CONTINGENCIA,
    STATUS_OPM_ATIVA,
    STATUS_QUE_IMPEDEM_MOVIMENTACAO,
    STATUS_QUE_IMPEDEM_NA_IMPLANTACAO,
)
from app.core.db import engine
from app.errors import (
    OpmInvalida,
    PlacaDuplicada,
    StatusNaoPermiteMovimentacao,
    ViaturaNaoEncontrada,
)

SQL_VIATURA = """
    SELECT v.id_viatura, v.placa, v.modelo, v.status_operacional,
           v.fk_id_opm_unidade AS id_opm, o.nome AS nome_opm
    FROM tb_viatura v
    LEFT JOIN tb_opm o ON o.id_opm = v.fk_id_opm_unidade
"""


def validar_opm_destino(conn: Connection, id_opm: int | None) -> str:
    """RF03: a OPM deve existir e estar ativa. Devolve o nome da OPM."""
    if id_opm is None or id_opm == ID_OPM_CONTINGENCIA:
        raise OpmInvalida()
    # FOR SHARE impede que a OPM seja inativada enquanto a transação está aberta.
    opm = conn.execute(
        text("SELECT nome, status FROM tb_opm WHERE id_opm = :id FOR SHARE"),
        {"id": id_opm},
    ).mappings().first()
    if opm is None or opm["status"] != STATUS_OPM_ATIVA:
        raise OpmInvalida()
    return opm["nome"]


def _registrar_historico(conn, id_viatura, id_opm_origem, id_opm_destino, tipo, usuario):
    conn.execute(
        text("""
            INSERT INTO tb_historico_movimentacao
                (id_viatura, id_opm_origem, id_opm_destino, tipo, usuario)
            VALUES (:viatura, :origem, :destino, :tipo, :usuario)
        """),
        {"viatura": id_viatura, "origem": id_opm_origem, "destino": id_opm_destino,
         "tipo": tipo, "usuario": usuario},
    )


def _registrar_notificacao(conn, id_viatura, id_opm_destino, mensagem):
    conn.execute(
        text("""
            INSERT INTO tb_notificacao_pendente (id_viatura, id_opm_destino, mensagem)
            VALUES (:viatura, :destino, :mensagem)
        """),
        {"viatura": id_viatura, "destino": id_opm_destino, "mensagem": mensagem},
    )


def _buscar_viatura(conn: Connection, id_viatura: int) -> dict:
    viatura = conn.execute(
        text(SQL_VIATURA + " WHERE v.id_viatura = :id"), {"id": id_viatura}
    ).mappings().first()
    return dict(viatura)


def mover_viatura(id_viatura: int, id_opm_destino: int | None, usuario: str,
                  tipo: str = "TRANSFERENCIA") -> dict:
    with engine.begin() as conn:
        return mover_viatura_na_transacao(conn, id_viatura, id_opm_destino, usuario, tipo)


def mover_viatura_na_transacao(conn: Connection, id_viatura: int, id_opm_destino: int | None,
                               usuario: str, tipo: str = "TRANSFERENCIA", implantacao: bool = False) -> dict:
    """Mesma regra de mover_viatura, dentro da transação de quem chama (operações em lote).

    implantacao=True: correção da lotação na aba Implantação, em que viatura cautelada pode mudar
    de OPM; a OPM de destino continua validada pelo RF03 e o histórico é gravado igual.
    """
    # FOR UPDATE serializa movimentações simultâneas da mesma viatura.
    atual = conn.execute(
        text("""
            SELECT placa, status_operacional, fk_id_opm_unidade
            FROM tb_viatura WHERE id_viatura = :id FOR UPDATE
        """),
        {"id": id_viatura},
    ).mappings().first()
    if atual is None:
        raise ViaturaNaoEncontrada(id_viatura)

    nome_destino = validar_opm_destino(conn, id_opm_destino)
    impedem = STATUS_QUE_IMPEDEM_NA_IMPLANTACAO if implantacao else STATUS_QUE_IMPEDEM_MOVIMENTACAO
    if atual["status_operacional"] in impedem:
        raise StatusNaoPermiteMovimentacao(atual["status_operacional"])

    conn.execute(
        text("""
            UPDATE tb_viatura
            SET fk_id_opm_unidade = :destino, dt_atualizacao = now()
            WHERE id_viatura = :id
        """),
        {"destino": id_opm_destino, "id": id_viatura},
    )
    _registrar_historico(conn, id_viatura, atual["fk_id_opm_unidade"],
                         id_opm_destino, tipo, usuario)
    _registrar_notificacao(conn, id_viatura, id_opm_destino,
                           f"Viatura {atual['placa']} lotada em {nome_destino}.")
    return _buscar_viatura(conn, id_viatura)


def criar_viatura(placa: str, modelo: str, id_opm: int | None, usuario: str) -> dict:
    try:
        with engine.begin() as conn:
            validar_opm_destino(conn, id_opm)
            id_viatura = conn.execute(
                text("""
                    INSERT INTO tb_viatura (placa, modelo, status_operacional, fk_id_opm_unidade)
                    VALUES (:placa, :modelo, 'DISPONIVEL', :opm)
                    RETURNING id_viatura
                """),
                {"placa": placa, "modelo": modelo, "opm": id_opm},
            ).scalar_one()
            _registrar_historico(conn, id_viatura, None, id_opm, "CRIACAO", usuario)
            return _buscar_viatura(conn, id_viatura)
    except IntegrityError as erro:
        if "placa" in str(erro.orig):
            raise PlacaDuplicada(placa) from erro
        raise


def listar_viaturas() -> list[dict]:
    with engine.connect() as conn:
        linhas = conn.execute(text(SQL_VIATURA + " ORDER BY v.placa")).mappings()
        return [dict(linha) for linha in linhas]
