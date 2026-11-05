"""Hierarquia das OPMs no banco de desenvolvimento (somente leitura, só tabelas de classificação).

    python -m avaliacao.hierarquia_opm --env-file <.env com DATABASE_URL>

Lista as colunas de sgpm.opm_tipo_orgao, sgpm.opm_tipo e sgpm.opm_nivel, o conteúdo dessas tabelas de
domínio (sem colunas de log) e quantas OPMs vigentes há em cada classificação.
"""

import argparse
import sys

from avaliacao.conexao import VIGENTE, ErroConexao, carregar_url, conectar, consultar

TABELAS = ("opm_tipo_orgao", "opm_tipo", "opm_nivel")


def colunas(conn, tabela: str) -> list[str]:
    linhas = consultar(conn, """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'sgpm' AND table_name = %(t)s ORDER BY ordinal_position""", {"t": tabela})
    return [linha["column_name"] for linha in linhas]


def imprimir(linhas: list[dict]) -> None:
    if not linhas:
        print("   (vazio)")
        return
    cols = list(linhas[0].keys())
    print("   " + " | ".join(cols))
    for linha in linhas:
        print("   " + " | ".join("" if linha[c] is None else str(linha[c]) for c in cols))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file")
    args = parser.parse_args(argv)
    try:
        with conectar(carregar_url(args.env_file)) as conn:
            for tabela in TABELAS:
                todas = colunas(conn, tabela)
                uteis = [c for c in todas if not c.startswith("log_")]
                print(f"\n=== sgpm.{tabela}: colunas {todas}")
                if uteis:
                    imprimir(consultar(conn, f"SELECT {', '.join(uteis)} FROM sgpm.{tabela} ORDER BY 1"))
            for tabela, coluna in (("opm_tipo_orgao", "cod_opm_tipo_orgao"), ("opm_tipo", "cod_opm_tipo"),
                                   ("opm_nivel", "cod_opm_nivel")):
                print(f"\n=== OPMs vigentes por {coluna}")
                imprimir(consultar(conn, f"""
                    SELECT o.{coluna}, count(*) AS opms_vigentes
                    FROM sgpm.opm o WHERE o.vigente = %(s)s GROUP BY 1 ORDER BY 1""", {"s": VIGENTE}))
    except ErroConexao as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
