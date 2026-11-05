"""De-para unidade antiga -> OPM, com validação humana (RF04).

Uso (dentro do container logistica-api):
    python -m scripts.de_para gerar
        Sugere a OPM de cada unidade antiga ainda sem de-para e exporta um CSV para revisão.
    python -m scripts.de_para importar relatorios/de_para_revisao_AAAAMMDD_HHMMSS.csv --usuario fulano
        Confirma as OPMs preenchidas na coluna id_opm_confirmada e, como na tela, lota na hora as
        viaturas dessas unidades que estão sem OPM ou na OPM 0 (movimentação com histórico;
        cautelada fica bloqueada).

Decisões já gravadas (inclusive as manuais) nunca são sobrescritas pelo `gerar`.
"""

import argparse
import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.db import engine
from app.errors import ErroDominio
from app.services.de_para import aplicar_de_para_na_contingencia, confirmar_de_para, sincronizar_de_para

CAMPOS_REVISAO = [
    "cd_unidade_legado", "ds_unidade_legado", "qtd_viaturas_ativas", "situacao", "metodo",
    "score", "id_opm_sugerida", "nome_opm_sugerida", "observacao", "id_opm_confirmada",
]


def exportar_para_revisao(conn: Connection, saida: Path) -> Path:
    linhas = conn.execute(text("""
        SELECT d.cd_unidade_legado, d.ds_unidade_legado,
               (SELECT count(*) FROM tb_viatura v
                WHERE v.cd_unidade_legado = d.cd_unidade_legado
                  AND v.status_operacional <> 'BAIXADA') AS qtd_viaturas_ativas,
               d.situacao, d.metodo, d.score, d.fk_id_opm AS id_opm_sugerida,
               o.nome AS nome_opm_sugerida, d.observacao
        FROM tb_de_para_unidade d
        LEFT JOIN tb_opm o ON o.id_opm = d.fk_id_opm
        ORDER BY (d.situacao = 'CONFIRMADO'), d.cd_unidade_legado
    """)).mappings().all()

    saida.mkdir(parents=True, exist_ok=True)
    caminho = saida / f"de_para_revisao_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_REVISAO, delimiter=";")
        escritor.writeheader()
        escritor.writerows({**linha, "id_opm_confirmada": ""} for linha in linhas)
    return caminho


def _ler_revisao(caminho: Path) -> list[dict]:
    """Lê o CSV revisado. O Excel pode salvar com ',' ou ';' e com/sem BOM, conforme a região."""
    conteudo = caminho.read_bytes()
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("cp1252")
    try:
        delimitador = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=";,\t").delimiter
    except csv.Error:
        delimitador = ";"
    leitor = csv.DictReader(texto.splitlines(), delimiter=delimitador)
    faltando = {"cd_unidade_legado", "id_opm_confirmada"} - set(leitor.fieldnames or [])
    if faltando:
        raise ValueError(f"Colunas ausentes no arquivo: {', '.join(sorted(faltando))}.")
    return [l for l in leitor if (l["id_opm_confirmada"] or "").strip()]


@dataclass
class ResultadoImportacao:
    confirmadas: int = 0
    movidas: list[str] = field(default_factory=list)
    bloqueadas: list[dict] = field(default_factory=list)


def importar_revisao(caminho: Path, usuario: str) -> ResultadoImportacao:
    """Confirma as linhas com id_opm_confirmada preenchido e aplica nas viaturas. Tudo ou nada (RNF01)."""
    linhas = _ler_revisao(caminho)
    resultado = ResultadoImportacao(confirmadas=len(linhas))

    with engine.begin() as conn:
        for numero, linha in enumerate(linhas, start=2):
            cd, id_opm = linha["cd_unidade_legado"], int(linha["id_opm_confirmada"])
            try:
                anterior = confirmar_de_para(conn, cd, id_opm, usuario)
                aplicacao = aplicar_de_para_na_contingencia(conn, cd, usuario, anterior)
            except ErroDominio as erro:
                raise ValueError(f"Linha {numero} (unidade {cd}, OPM {id_opm}): {erro.mensagem}") from erro
            resultado.movidas += aplicacao["movidas"]
            resultado.bloqueadas += aplicacao["bloqueadas"]
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    comandos = parser.add_subparsers(dest="comando", required=True)
    gerar = comandos.add_parser("gerar", help="sugere o de-para e exporta CSV para revisão")
    gerar.add_argument("--saida", type=Path, default=Path("relatorios"))
    importar = comandos.add_parser("importar", help="aplica o CSV revisado")
    importar.add_argument("arquivo", type=Path)
    importar.add_argument("--usuario", required=True, help="quem validou o de-para")
    args = parser.parse_args()

    if args.comando == "gerar":
        with engine.begin() as conn:
            criadas = sincronizar_de_para(conn)
            caminho = exportar_para_revisao(conn, args.saida)
        print(f"De-para criado para {criadas} unidade(s) antiga(s).")
        print(f"Revise e preencha id_opm_confirmada em: {caminho}")
    else:
        resultado = importar_revisao(args.arquivo, args.usuario)
        print(f"{resultado.confirmadas} correspondência(s) confirmada(s).")
        print(f"Lotadas na OPM confirmada: {', '.join(resultado.movidas) or 'nenhuma viatura'}.")
        if resultado.bloqueadas:
            bloqueadas = ", ".join(f"{b['placa']} ({b['status']})" for b in resultado.bloqueadas)
            print(f"Ficaram de fora (movimentação bloqueada): {bloqueadas}.")


if __name__ == "__main__":
    main()
