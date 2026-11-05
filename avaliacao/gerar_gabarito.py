"""Monta o gabarito UPM -> OPM a partir do histórico dos veículos (sem depender de nomes).

Uma UPM entra no gabarito quando as viaturas que têm as duas colunas preenchidas estão (quase)
todas na mesma OPM, e essa OPM é vigente (S). Como o gabarito vem dos códigos e a regra atual e a
IA só enxergam os NOMES, ele mede de forma justa quanto cada método acerta pelo nome.

    python -m avaliacao.gerar_gabarito --env-file <.env com DATABASE_URL> [--pureza-minima 1.0]

Saída (contém nomes de unidades reais, fica fora do git em dados_reais/):
    dados_reais/gabarito_upm_opm.csv
    dados_reais/opms_vigentes.csv
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from avaliacao.conexao import VIGENTE, ErroConexao, carregar_url, conectar, consultar

RAIZ = Path(__file__).resolve().parent.parent

CONSULTAS = {
    "gabarito": """
        WITH par AS (SELECT cod_upm, cod_opm, count(*) n FROM transporte.tb_veiculo
                     WHERE cod_upm IS NOT NULL AND cod_opm IS NOT NULL GROUP BY 1, 2),
             tot AS (SELECT cod_upm, sum(n) t FROM par GROUP BY 1),
             dom AS (SELECT DISTINCT ON (p.cod_upm) p.cod_upm, p.cod_opm, p.n, t.t
                     FROM par p JOIN tot t USING (cod_upm) ORDER BY p.cod_upm, p.n DESC, p.cod_opm)
        SELECT d.cod_upm, trim(u.upm) AS descricao_upm, d.cod_opm AS cod_opm_gabarito,
               d.t AS n_veiculos, round(d.n::numeric / d.t, 3) AS pureza
        FROM dom d
        JOIN geral.tb_upm u ON u.cod_upm = d.cod_upm
        JOIN sgpm.opm o ON o.cod_opm = d.cod_opm
        WHERE o.vigente = %(s)s AND u.upm IS NOT NULL AND trim(u.upm) <> ''
          AND d.n::numeric / d.t >= %(pureza)s
        ORDER BY d.cod_upm""",
    "opms_vigentes": """
        SELECT cod_opm, trim(opm) AS opm, trim(opm_abreviatura) AS opm_abreviatura
        FROM sgpm.opm WHERE vigente = %(s)s AND opm IS NOT NULL AND trim(opm) <> ''
        ORDER BY cod_opm""",
}

ARQ_GABARITO = "gabarito_upm_opm.csv"
ARQ_OPMS = "opms_vigentes.csv"


def gravar_csv(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:  # abre direto no Excel
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file")
    parser.add_argument("--pureza-minima", type=float, default=1.0,
                        help="fração mínima das viaturas da UPM na OPM dominante (padrão 1.0 = todas)")
    parser.add_argument("--saida", default=str(RAIZ / "dados_reais"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        with conectar(carregar_url(args.env_file)) as conn:
            params = {"s": VIGENTE, "pureza": args.pureza_minima}
            gabarito = consultar(conn, CONSULTAS["gabarito"], params)
            opms = consultar(conn, CONSULTAS["opms_vigentes"], params)
    except ErroConexao as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 2
    if not gabarito or not opms:
        print("ERRO: consulta não retornou dados para o gabarito.", file=sys.stderr)
        return 1

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    gravar_csv(saida / ARQ_GABARITO, gabarito)
    gravar_csv(saida / ARQ_OPMS, opms)
    print(f"Gabarito: {len(gabarito)} UPM(s) com pureza >= {args.pureza_minima} | "
          f"OPMs vigentes candidatas: {len(opms)}")
    print(f"Arquivos (fora do git): {saida / ARQ_GABARITO}, {saida / ARQ_OPMS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
