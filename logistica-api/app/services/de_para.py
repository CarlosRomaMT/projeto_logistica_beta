"""Comparação entre a descrição da unidade antiga e o nome da OPM (RF04).

A descrição é a única ponte entre os cadastros e não é 100% confiável (abreviações,
grafias diferentes). Por isso só a igualdade exata, após normalizar, é confirmada
automaticamente; semelhança vira sugestão para validação humana.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import (
    ID_OPM_CONTINGENCIA,
    STATUS_BAIXADA,
    STATUS_OPM_ATIVA,
    STATUS_QUE_IMPEDEM_NA_IMPLANTACAO,
)
from app.core.db import engine
from app.errors import DeParaNaoEncontrado
from app.services.movimentacao import mover_viatura_na_transacao, validar_opm_destino

# Ponto de partida fictício: o dicionário real deve ser montado com quem conhece o cadastro.
ABREVIACOES = {
    "bpm": "batalhao policia militar",
    "btl": "batalhao",
    "bat": "batalhao",
    "cia": "companhia",
    "ind": "independente",
    "indep": "independente",
    "pm": "policia militar",
    "primeiro": "1", "primeira": "1",
    "segundo": "2", "segunda": "2",
    "terceiro": "3", "terceira": "3",
    "quarto": "4", "quarta": "4",
    "quinto": "5", "quinta": "5",
}
PALAVRAS_IGNORADAS = {"de", "do", "da", "dos", "das", "e"}

LIMIAR_SUGESTAO = 0.75
# Se a segunda melhor OPM ficar a menos disso da primeira, a sugestão é marcada como ambígua.
MARGEM_AMBIGUIDADE = 0.05

SITUACAO_CONFIRMADO = "CONFIRMADO"
SITUACAO_PENDENTE = "PENDENTE"
SITUACAO_SEM_CORRESPONDENCIA = "SEM_CORRESPONDENCIA"


def normalizar(texto: str) -> list[str]:
    """'1º B.P.M. - Centro' -> ['1', 'batalhao', 'policia', 'militar', 'centro']"""
    texto = texto.lower()
    for ordinal in ("º", "ª", "°"):
        texto = texto.replace(ordinal, " ")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.replace(".", "")              # B.P.M. -> bpm
    texto = re.sub(r"\b(\d+)[oa]\b", r"\1", texto)  # 1o, 1a -> 1
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    tokens = []
    for token in texto.split():
        tokens.extend(ABREVIACOES.get(token, token).split())
    return [t for t in tokens if t not in PALAVRAS_IGNORADAS]


def similaridade(a: list[str], b: list[str]) -> float:
    # Números identificam a unidade (1º x 2º BPM): se diferem, não há correspondência.
    if {t for t in a if t.isdigit()} != {t for t in b if t.isdigit()}:
        return 0.0
    return SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()


@dataclass
class Sugestao:
    situacao: str
    id_opm: int | None
    metodo: str | None
    score: float
    ambigua: bool = False


def sugerir_opm(descricao: str, opms: list[dict]) -> Sugestao:
    """opms: [{'id_opm': ..., 'nome': ...}] candidatas (sem a OPM de contingência)."""
    alvo = normalizar(descricao)
    pontuadas = sorted(
        ((similaridade(alvo, normalizar(o["nome"])), o["id_opm"]) for o in opms),
        reverse=True,
    )
    exatas = [id_opm for score, id_opm in pontuadas if score == 1.0]
    if len(exatas) == 1:
        return Sugestao(SITUACAO_CONFIRMADO, exatas[0], "EXATO", 1.0)
    if not pontuadas or pontuadas[0][0] < LIMIAR_SUGESTAO:
        melhor = pontuadas[0][0] if pontuadas else 0.0
        return Sugestao(SITUACAO_SEM_CORRESPONDENCIA, None, None, round(melhor, 3))
    score, id_opm = pontuadas[0]
    ambigua = len(pontuadas) > 1 and score - pontuadas[1][0] < MARGEM_AMBIGUIDADE
    return Sugestao(SITUACAO_PENDENTE, id_opm, "SIMILARIDADE", round(score, 3), ambigua)


# --- Persistência do de-para (tb_de_para_unidade) e sua aplicação nas viaturas ---


def sincronizar_de_para(conn: Connection) -> int:
    """Cria o de-para das unidades antigas que ainda não têm um. Devolve quantas criou.

    Decisões já gravadas (inclusive as manuais) nunca são sobrescritas. Pode rodar em paralelo
    (subida da API com vários workers, carga): quem chegar depois ignora o que já foi criado.
    """
    opms = conn.execute(
        text("SELECT id_opm, nome FROM tb_opm WHERE id_opm <> :contingencia"),
        {"contingencia": ID_OPM_CONTINGENCIA},
    ).mappings().all()
    novas = conn.execute(text("""
        SELECT u.cd_unidade, u.ds_unidade
        FROM tb_unidade_legado u
        LEFT JOIN tb_de_para_unidade d ON d.cd_unidade_legado = u.cd_unidade
        WHERE d.cd_unidade_legado IS NULL
        ORDER BY u.cd_unidade
    """)).mappings().all()

    criadas = 0
    for unidade in novas:
        sugestao = sugerir_opm(unidade["ds_unidade"], opms)
        criadas += conn.execute(
            text("""
                INSERT INTO tb_de_para_unidade
                    (cd_unidade_legado, ds_unidade_legado, fk_id_opm, situacao, metodo, score, observacao)
                VALUES (:cd, :ds, :opm, :situacao, :metodo, :score, :obs)
                ON CONFLICT (cd_unidade_legado) DO NOTHING
            """),
            {"cd": unidade["cd_unidade"], "ds": unidade["ds_unidade"], "opm": sugestao.id_opm,
             "situacao": sugestao.situacao, "metodo": sugestao.metodo, "score": sugestao.score,
             "obs": "Ambígua: outra OPM com pontuação próxima" if sugestao.ambigua else None},
        ).rowcount
    return criadas


def mapa_de_para(conn: Connection) -> dict[str, dict]:
    linhas = conn.execute(text("""
        SELECT d.cd_unidade_legado, d.ds_unidade_legado, d.situacao, d.fk_id_opm,
               o.nome AS nome_opm, o.status AS status_opm
        FROM tb_de_para_unidade d
        LEFT JOIN tb_opm o ON o.id_opm = d.fk_id_opm
    """)).mappings()
    return {linha["cd_unidade_legado"].strip(): dict(linha) for linha in linhas}


def resolver_opm(cd_legado: str | None, mapa: dict) -> tuple[int | None, str | None]:
    """Devolve (id_opm, None) se há de-para confirmado para OPM ativa, ou (None, motivo)."""
    codigo = (cd_legado or "").strip()
    if not codigo:
        return None, "LEGADO_NULO"
    de_para = mapa.get(codigo)
    if de_para is None:
        return None, "UNIDADE_LEGADO_INEXISTENTE"
    if de_para["situacao"] == SITUACAO_PENDENTE:
        return None, "DE_PARA_PENDENTE_VALIDACAO"
    if de_para["situacao"] != SITUACAO_CONFIRMADO:
        return None, "SEM_CORRESPONDENCIA"
    if de_para["status_opm"] != STATUS_OPM_ATIVA:
        return None, "OPM_INATIVA"
    return de_para["fk_id_opm"], None


def atualizar_viatura_da_contingencia(conn: Connection, id_viatura: int, id_opm: int) -> bool:
    """Usado pela carga em lote: grava só se a viatura está sem OPM ou na contingência."""
    return conn.execute(
        text("""
            UPDATE tb_viatura SET fk_id_opm_unidade = :opm, dt_atualizacao = now()
            WHERE id_viatura = :id
              AND (fk_id_opm_unidade IS NULL OR fk_id_opm_unidade = :contingencia)
              AND fk_id_opm_unidade IS DISTINCT FROM :opm
        """),
        {"opm": id_opm, "id": id_viatura, "contingencia": ID_OPM_CONTINGENCIA},
    ).rowcount > 0


def confirmar_de_para(conn: Connection, cd_unidade: str, id_opm: int | None, usuario: str) -> int | None:
    """Decisão humana: a unidade antiga corresponde a esta OPM (que deve existir e estar ativa).

    Também altera uma associação já confirmada (inclusive a automática). Devolve a OPM anterior
    quando a unidade já estava confirmada, para aplicar_de_para_na_contingencia corrigir o que a
    carga lotou por ela.
    """
    validar_opm_destino(conn, id_opm)
    atual = conn.execute(
        text("SELECT situacao, fk_id_opm FROM tb_de_para_unidade WHERE cd_unidade_legado = :cd FOR UPDATE"),
        {"cd": cd_unidade},
    ).mappings().first()
    if atual is None:
        raise DeParaNaoEncontrado(cd_unidade)
    conn.execute(
        text("""
            UPDATE tb_de_para_unidade
            SET fk_id_opm = :opm, situacao = :confirmado, metodo = 'MANUAL',
                confirmado_por = :usuario, dt_confirmacao = now(), dt_atualizacao = now()
            WHERE cd_unidade_legado = :cd
        """),
        {"opm": id_opm, "confirmado": SITUACAO_CONFIRMADO, "usuario": usuario, "cd": cd_unidade},
    )
    return atual["fk_id_opm"] if atual["situacao"] == SITUACAO_CONFIRMADO else None


def aplicar_de_para_na_contingencia(conn: Connection, cd_unidade: str, usuario: str,
                                    id_opm_anterior: int | None = None) -> dict:
    """Move para a OPM confirmada as viaturas desse código que estão sem OPM ou na contingência.

    Se a associação foi alterada, move também as que a carga lotou na OPM anterior e que nunca
    foram movimentadas pelo sistema novo (sem histórico): a lotação delas veio só da associação.
    Passa pelo serviço de movimentação (histórico, notificação, regra de status). Viaturas com
    status que impede movimentação ficam onde estão e são devolvidas como bloqueadas.
    """
    id_opm = buscar_de_para(conn, cd_unidade)["id_opm"]
    viaturas = conn.execute(
        text("""
            SELECT id_viatura, placa, status_operacional FROM tb_viatura v
            WHERE cd_unidade_legado = :cd
              AND status_operacional <> :baixada
              AND (fk_id_opm_unidade IS NULL OR fk_id_opm_unidade = :contingencia
                   OR (fk_id_opm_unidade = :anterior AND fk_id_opm_unidade <> :opm
                       AND NOT EXISTS (SELECT 1 FROM tb_historico_movimentacao h
                                       WHERE h.id_viatura = v.id_viatura)))
            ORDER BY placa
        """),
        {"cd": cd_unidade, "contingencia": ID_OPM_CONTINGENCIA, "baixada": STATUS_BAIXADA,
         "anterior": id_opm_anterior, "opm": id_opm},
    ).mappings().all()

    movidas, bloqueadas = [], []
    for v in viaturas:
        if v["status_operacional"] in STATUS_QUE_IMPEDEM_NA_IMPLANTACAO:
            bloqueadas.append({"placa": v["placa"], "status": v["status_operacional"]})
        else:
            mover_viatura_na_transacao(conn, v["id_viatura"], id_opm, usuario, "CORRECAO_DE_PARA", implantacao=True)
            movidas.append(v["placa"])
    return {"movidas": movidas, "bloqueadas": bloqueadas}


SQL_DE_PARA = """
    SELECT d.cd_unidade_legado, d.ds_unidade_legado, d.situacao, d.metodo, d.score,
           d.fk_id_opm AS id_opm, o.nome AS nome_opm, d.observacao,
           d.confirmado_por, d.dt_confirmacao, o.status AS status_opm,
           (SELECT count(*) FROM tb_viatura v
            WHERE v.cd_unidade_legado = d.cd_unidade_legado
              AND v.status_operacional <> 'BAIXADA'
              AND (v.fk_id_opm_unidade IS NULL OR v.fk_id_opm_unidade = 0)) AS qtd_viaturas_contingencia
    FROM tb_de_para_unidade d
    LEFT JOIN tb_opm o ON o.id_opm = d.fk_id_opm
"""


def buscar_de_para(conn: Connection, cd_unidade: str) -> dict:
    linha = conn.execute(
        text(SQL_DE_PARA + " WHERE d.cd_unidade_legado = :cd"), {"cd": cd_unidade}
    ).mappings().first()
    if linha is None:
        raise DeParaNaoEncontrado(cd_unidade)
    return dict(linha)


def listar_de_para() -> list[dict]:
    """Pendentes, sem correspondência e associadas a OPM inativa primeiro; depois as que mais
    deixam viaturas na contingência."""
    with engine.connect() as conn:
        linhas = conn.execute(text(
            SQL_DE_PARA + " ORDER BY (d.situacao = 'CONFIRMADO' AND o.status = 'ATIVA'),"
            " qtd_viaturas_contingencia DESC, d.cd_unidade_legado"
        )).mappings()
        return [dict(linha) for linha in linhas]
