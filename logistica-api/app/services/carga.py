"""RF04: carga que preenche fk_id_opm_unidade a partir do cd_unidade_legado.

Usada pelo script `scripts.migrar_opm_legado` e pelo painel "Carga da lotação" (aba Implantação, etapa 2).

Regras:
- A unidade antiga só vira OPM por um de-para CONFIRMADO (tb_de_para_unidade). Unidades novas
  ganham sugestão automática no início da carga; só igualdade exata de nome é confirmada sozinha.
- Viaturas ativas (não BAIXADA) sem OPM ou na OPM de contingência são (re)avaliadas: depois que
  alguém confirma um de-para, rodar a carga de novo tira as viaturas da contingência.
- Legado nulo, inexistente, de-para pendente/sem correspondência ou OPM inativa: contingência + relatório.
- Viatura cautelada é lotada como as demais (na implantação a cautela não impede a lotação).
- Viaturas nunca movimentadas pelo sistema novo cuja coluna nova diverge do legado não são
  alteradas: viram propostas de correção, que só são aplicadas com decisão humana.
- Tudo numa única transação (RNF01). A simulação (dry_run) desfaz tudo ao final.
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.core.config import ID_OPM_CONTINGENCIA, STATUS_BAIXADA, STATUS_OPM_ATIVA
from app.core.db import engine
from app.errors import ViaturaForaDaContingencia, ViaturaNaoEncontrada
from app.services import de_para as servico_de_para
from app.services.de_para import SITUACAO_PENDENTE, mapa_de_para, resolver_opm, sincronizar_de_para
from app.services.divergencias import gerar_propostas, listar_divergencias
from app.services.movimentacao import mover_viatura_na_transacao

DIR_RELATORIOS = Path("relatorios")
CAMPOS_RELATORIO = [
    "id_viatura", "placa", "cd_unidade_legado", "ds_unidade_legado", "fk_id_opm_unidade",
    "motivo", "opm_sugerida", "acao", "executado_por",
]
# Só os relatórios gerados aqui podem ser baixados pela API (sem caminhos arbitrários).
PADRAO_RELATORIO = re.compile(r"inconformidades_\d{8}_\d{6}\.csv")


@dataclass
class ResultadoMigracao:
    atualizadas: int = 0
    contingencia: int = 0
    de_para_criados: int = 0
    propostas_criadas: int = 0
    # Viaturas que saem de "sem OPM" ou da OPM 0 para a OPM do de-para confirmado.
    lotadas: list[dict] = field(default_factory=list)
    inconformidades: list[dict] = field(default_factory=list)
    relatorio: Path | None = None


def _descrever(cd_legado: str | None, mapa: dict) -> dict:
    de_para = mapa.get((cd_legado or "").strip()) or {}
    sugerida = de_para.get("nome_opm") if de_para.get("situacao") == SITUACAO_PENDENTE else None
    return {"ds_unidade_legado": de_para.get("ds_unidade_legado"), "opm_sugerida": sugerida}


def _gravar_relatorio(inconformidades: list[dict], saida: Path, executado_por: str) -> Path:
    saida.mkdir(parents=True, exist_ok=True)
    caminho = saida / f"inconformidades_{datetime.now():%Y%m%d_%H%M%S}.csv"
    # utf-8-sig e ';' para abrir direto no Excel em pt-BR.
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_RELATORIO, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows({**item, "executado_por": executado_por} for item in inconformidades)
    return caminho


def contar_aguardando_carga() -> int:
    """Viaturas ativas ainda sem OPM: invisíveis no Cautela até a carga rodar."""
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM tb_viatura WHERE fk_id_opm_unidade IS NULL AND status_operacional <> :baixada"),
            {"baixada": STATUS_BAIXADA},
        ).scalar()


def listar_sem_opm() -> list[dict]:
    """Viaturas ativas na OPM 0: o que a carga não resolveu, para lotar uma a uma (etapa 4)."""
    with engine.connect() as conn:
        mapa = mapa_de_para(conn)
        viaturas = conn.execute(
            text("""
                SELECT v.id_viatura, v.placa, v.modelo, v.status_operacional, v.cd_unidade_legado,
                       u.ds_unidade AS ds_unidade_legado
                FROM tb_viatura v
                LEFT JOIN tb_unidade_legado u ON u.cd_unidade = trim(v.cd_unidade_legado)
                WHERE v.fk_id_opm_unidade = :contingencia AND v.status_operacional <> :baixada
                ORDER BY v.placa
            """),
            {"contingencia": ID_OPM_CONTINGENCIA, "baixada": STATUS_BAIXADA},
        ).mappings().all()

    resultado = []
    for v in viaturas:
        _, motivo = resolver_opm(v["cd_unidade_legado"], mapa)
        de_para = mapa.get((v["cd_unidade_legado"] or "").strip()) or {}
        # Sugestão só quando a OPM do de-para pode receber a viatura.
        sugerida = de_para if de_para.get("fk_id_opm") and de_para.get("status_opm") == STATUS_OPM_ATIVA else {}
        resultado.append({**v, "motivo": motivo, "id_opm_sugerida": sugerida.get("fk_id_opm"),
                          "nome_opm_sugerida": sugerida.get("nome_opm")})
    return resultado


def lotar_da_contingencia(id_viatura: int, id_opm: int | None, usuario: str) -> dict:
    """Etapa 4: tira uma viatura da OPM 0 pela movimentação, com a regra da implantação.

    Só vale para viatura que está na OPM 0: fora disso, a movimentação comum (RF03) é o caminho.
    """
    with engine.begin() as conn:
        atual = conn.execute(
            text("SELECT placa, fk_id_opm_unidade FROM tb_viatura WHERE id_viatura = :id FOR UPDATE"),
            {"id": id_viatura},
        ).mappings().first()
        if atual is None:
            raise ViaturaNaoEncontrada(id_viatura)
        if atual["fk_id_opm_unidade"] != ID_OPM_CONTINGENCIA:
            raise ViaturaForaDaContingencia(atual["placa"])
        return mover_viatura_na_transacao(conn, id_viatura, id_opm, usuario, "LOTACAO_IMPLANTACAO", implantacao=True)


def caminho_relatorio(nome: str) -> Path | None:
    caminho = DIR_RELATORIOS / nome
    return caminho if PADRAO_RELATORIO.fullmatch(nome) and caminho.is_file() else None


def executar_migracao(
    dry_run: bool = False, saida: Path | None = None, executado_por: str = "terminal"
) -> ResultadoMigracao:
    saida = saida or DIR_RELATORIOS
    resultado = ResultadoMigracao()
    try:
        with engine.connect() as conn, conn.begin() as transacao:
            resultado.de_para_criados = sincronizar_de_para(conn)
            mapa = mapa_de_para(conn)
            pendentes = conn.execute(
                text("""
                    SELECT id_viatura, placa, cd_unidade_legado, status_operacional FROM tb_viatura
                    WHERE (fk_id_opm_unidade IS NULL OR fk_id_opm_unidade = :contingencia)
                      AND status_operacional <> :baixada
                    ORDER BY id_viatura
                    FOR UPDATE
                """),
                {"contingencia": ID_OPM_CONTINGENCIA, "baixada": STATUS_BAIXADA},
            ).mappings().all()

            for v in pendentes:
                id_opm, motivo = resolver_opm(v["cd_unidade_legado"], mapa)
                descricao = _descrever(v["cd_unidade_legado"], mapa)
                if motivo:
                    id_opm = ID_OPM_CONTINGENCIA
                    resultado.contingencia += 1
                    resultado.inconformidades.append(
                        {**v, **descricao, "fk_id_opm_unidade": id_opm, "motivo": motivo,
                         "acao": "MANTIDA_NA_OPM_CONTINGENCIA"}
                    )
                if servico_de_para.atualizar_viatura_da_contingencia(conn, v["id_viatura"], id_opm):
                    resultado.atualizadas += 1
                    if not motivo:
                        de_para = mapa[v["cd_unidade_legado"].strip()]
                        resultado.lotadas.append(
                            {"placa": v["placa"], "cd_unidade_legado": v["cd_unidade_legado"],
                             "ds_unidade_legado": de_para["ds_unidade_legado"], "nome_opm": de_para["nome_opm"]}
                        )

            for d in listar_divergencias(conn, mapa):
                resultado.inconformidades.append(
                    {"id_viatura": d["id_viatura"], "placa": d["placa"],
                     "cd_unidade_legado": d["cd_unidade_legado"],
                     "fk_id_opm_unidade": d["fk_id_opm_unidade"],
                     **_descrever(d["cd_unidade_legado"], mapa),
                     "motivo": "DIVERGENCIA_LEGADO_X_NOVO", "acao": "PROPOSTA_DE_CORRECAO"}
                )
            resultado.propostas_criadas = gerar_propostas(conn)

            if dry_run:
                transacao.rollback()
            else:
                # Gravado antes do commit: se o CSV falhar, a carga também é desfeita.
                resultado.relatorio = _gravar_relatorio(resultado.inconformidades, saida, executado_por)
    except Exception:
        if resultado.relatorio:
            resultado.relatorio.unlink(missing_ok=True)
        raise
    return resultado
