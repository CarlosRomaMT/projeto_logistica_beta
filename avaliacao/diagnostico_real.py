"""Diagnóstico da lotação de viaturas no banco de desenvolvimento (evidência dos itens 05 e 06).

Somente leitura e só agregados: o relatório não traz nenhum nome, placa ou identificador de viatura.

    python -m avaliacao.diagnostico_real --env-file <caminho do .env com DATABASE_URL>

Saída: evidencias/diagnostico_real_<data>.md e .json
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from avaliacao.conexao import (
    NAO_VIGENTE,
    SITUACOES_OPERACIONAIS,
    VIGENTE,
    ErroConexao,
    carregar_url,
    conectar,
    consultar,
)

logger = logging.getLogger("diagnostico")
RAIZ = Path(__file__).resolve().parent.parent

# Correspondência UPM -> OPM deduzida dos veículos que têm as duas colunas preenchidas.
_DOMINANTE = """
    par AS (SELECT cod_upm, cod_opm, count(*) n FROM transporte.tb_veiculo
            WHERE cod_upm IS NOT NULL AND cod_opm IS NOT NULL GROUP BY 1, 2),
    tot AS (SELECT cod_upm, sum(n) t, count(*) k FROM par GROUP BY 1),
    dom AS (SELECT DISTINCT ON (p.cod_upm) p.cod_upm, p.cod_opm, p.n, t.t, t.k
            FROM par p JOIN tot t USING (cod_upm) ORDER BY p.cod_upm, p.n DESC, p.cod_opm)
"""

CONSULTAS = {
    "estrutura_fks": """
        SELECT kcu.column_name AS coluna, count(*) AS fks
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'transporte'
          AND tc.table_name = 'tb_veiculo' AND kcu.column_name IN ('cod_upm', 'cod_opm')
        GROUP BY 1""",
    "volumes": """
        SELECT (SELECT count(*) FROM transporte.tb_veiculo) AS veiculos,
               (SELECT count(*) FROM transporte.tb_veiculo WHERE cod_situacao = ANY(%(sit)s)) AS veiculos_operacionais,
               (SELECT count(*) FROM geral.tb_upm) AS upms,
               (SELECT count(*) FROM sgpm.opm) AS opms""",
    "opm_vigencia": """
        SELECT CASE WHEN vigente = %(s)s THEN 'vigente (S)' WHEN vigente = %(n)s THEN 'não vigente (N)'
                    ELSE 'desconsiderada (E/C/outros)' END AS vigencia, count(*) AS opms
        FROM sgpm.opm GROUP BY 1 ORDER BY 1""",
    "lotacao_operacional": """
        SELECT CASE WHEN v.cod_opm IS NULL THEN '1. sem cod_opm (invisível no Cautela)'
                    WHEN o.cod_opm IS NULL THEN '2. cod_opm inexistente em sgpm.opm (invisível)'
                    WHEN o.vigente = %(n)s THEN '3. OPM não vigente (sem check-in)'
                    WHEN o.vigente <> %(s)s OR o.vigente IS NULL THEN '4. OPM com vigência desconsiderada (E/C)'
                    ELSE '5. OPM vigente (OK)' END AS situacao, count(*) AS viaturas
        FROM transporte.tb_veiculo v LEFT JOIN sgpm.opm o ON o.cod_opm = v.cod_opm
        WHERE v.cod_situacao = ANY(%(sit)s) GROUP BY 1 ORDER BY 1""",
    "sem_opm_por_situacao": """
        SELECT s.cod_situacao, s.descricao, count(*) AS viaturas_sem_cod_opm
        FROM transporte.tb_veiculo v JOIN transporte.tb_veiculo_situacao s ON s.cod_situacao = v.cod_situacao
        WHERE v.cod_opm IS NULL GROUP BY 1, 2 ORDER BY 1""",
    "integridade": """
        SELECT
          count(*) FILTER (WHERE v.cod_upm IS NOT NULL AND u.cod_upm IS NULL) AS cod_upm_orfao,
          count(*) FILTER (WHERE v.cod_upm IS NOT NULL AND u.cod_upm IS NULL AND v.cod_situacao = ANY(%(sit)s)) AS cod_upm_orfao_operacional,
          count(*) FILTER (WHERE v.cod_opm IS NOT NULL AND o.cod_opm IS NULL) AS cod_opm_inexistente,
          count(*) FILTER (WHERE v.cod_opm IS NOT NULL AND o.cod_opm IS NULL AND v.cod_situacao = ANY(%(sit)s)) AS cod_opm_inexistente_operacional,
          count(*) FILTER (WHERE v.cod_upm IS NULL AND v.cod_opm IS NULL) AS sem_nenhuma_lotacao
        FROM transporte.tb_veiculo v
        LEFT JOIN geral.tb_upm u ON u.cod_upm = v.cod_upm
        LEFT JOIN sgpm.opm o ON o.cod_opm = v.cod_opm""",
    "ponte_opm_cod_upm": """
        SELECT count(*) AS opms, count(o.cod_upm) AS com_cod_upm,
               count(u.cod_upm) AS cod_upm_valido
        FROM sgpm.opm o LEFT JOIN geral.tb_upm u ON u.cod_upm = o.cod_upm""",
    "empirico_pureza": f"""
        WITH {_DOMINANTE}
        SELECT CASE WHEN k = 1 THEN 'a. todas as viaturas numa única OPM'
                    WHEN n::numeric / t >= 0.8 THEN 'b. OPM dominante com 80 por cento ou mais'
                    ELSE 'c. espalhada' END AS faixa,
               count(*) AS upms, sum(t) AS viaturas
        FROM dom GROUP BY 1 ORDER BY 1""",
    "empirico_reverso": """
        SELECT k AS upms_por_opm, count(*) AS opms FROM (
          SELECT cod_opm, count(DISTINCT cod_upm) k FROM transporte.tb_veiculo
          WHERE cod_upm IS NOT NULL AND cod_opm IS NOT NULL GROUP BY 1) x
        GROUP BY 1 ORDER BY 1""",
    "cobertura_sem_opm": f"""
        WITH {_DOMINANTE}
        SELECT (v.cod_situacao = ANY(%(sit)s)) AS operacional,
               CASE WHEN u.cod_upm IS NULL THEN '5. UPM órfã (sem nome: nada resolve)'
                    WHEN d.cod_upm IS NULL THEN '4. UPM sem histórico (alvo da IA por nome)'
                    WHEN o.vigente IS DISTINCT FROM %(s)s THEN '3. dominante não vigente (buscar sucessora)'
                    WHEN d.n::numeric / d.t >= 0.8 THEN '1. resolvível pelo histórico (confiável)'
                    ELSE '2. histórico fraco (revisão humana)' END AS resolucao,
               count(*) AS viaturas
        FROM transporte.tb_veiculo v
        LEFT JOIN geral.tb_upm u ON u.cod_upm = v.cod_upm
        LEFT JOIN dom d ON d.cod_upm = v.cod_upm
        LEFT JOIN sgpm.opm o ON o.cod_opm = d.cod_opm
        WHERE v.cod_opm IS NULL GROUP BY 1, 2 ORDER BY 1 DESC, 2""",
    "divergencias_operacional": f"""
        WITH {_DOMINANTE}
        SELECT CASE WHEN v.cod_opm = d.cod_opm THEN 'igual à dominante'
                    WHEN d.n::numeric / d.t >= 0.8 THEN 'DIVERGENTE em UPM confiável'
                    ELSE 'divergente em UPM espalhada' END AS comparacao,
               count(*) AS viaturas
        FROM transporte.tb_veiculo v JOIN dom d ON d.cod_upm = v.cod_upm
        WHERE v.cod_opm IS NOT NULL AND v.cod_situacao = ANY(%(sit)s) GROUP BY 1 ORDER BY 1""",
    "upms_sem_historico": f"""
        WITH {_DOMINANTE}
        SELECT count(*) AS upms_sem_historico FROM geral.tb_upm u
        WHERE NOT EXISTS (SELECT 1 FROM dom d WHERE d.cod_upm = u.cod_upm)""",
    "qualidade_nomes": """
        SELECT 'geral.tb_upm' AS tabela, count(*) AS total,
               count(*) FILTER (WHERE upm IS NULL OR trim(upm) = '') AS nome_vazio,
               count(sigla) AS com_sigla,
               (SELECT count(*) FROM (SELECT upper(trim(upm)) FROM geral.tb_upm GROUP BY 1 HAVING count(*) > 1) x) AS nomes_duplicados
        FROM geral.tb_upm
        UNION ALL
        SELECT 'sgpm.opm (vigentes)', count(*),
               count(*) FILTER (WHERE opm IS NULL OR trim(opm) = ''),
               count(opm_abreviatura),
               (SELECT count(*) FROM (SELECT upper(trim(opm)) FROM sgpm.opm WHERE vigente = %(s)s GROUP BY 1 HAVING count(*) > 1) y)
        FROM sgpm.opm WHERE vigente = %(s)s""",
}

TITULOS = {
    "estrutura_fks": "Chaves estrangeiras em tb_veiculo.cod_upm / cod_opm",
    "volumes": "Volumes",
    "opm_vigencia": "Vigência das OPMs (S = vigente, N = não; E/C desconsideradas)",
    "lotacao_operacional": "Lotação da frota operacional (situações 1, 2 e 8)",
    "sem_opm_por_situacao": "Viaturas sem cod_opm por situação (frota inteira)",
    "integridade": "Integridade referencial (as colunas não têm FK)",
    "ponte_opm_cod_upm": "Ponte existente sgpm.opm.cod_upm",
    "empirico_pureza": "De-para deduzido do histórico: pureza por UPM",
    "empirico_reverso": "De-para deduzido: quantas UPMs caem na mesma OPM (relação N:1)",
    "cobertura_sem_opm": "Viaturas sem cod_opm: como cada uma pode ser resolvida",
    "divergencias_operacional": "Frota operacional com as duas colunas: OPM atual x OPM dominante da UPM",
    "upms_sem_historico": "UPMs sem nenhuma viatura com as duas colunas (só o nome resolve)",
    "qualidade_nomes": "Qualidade dos nomes (insumo da comparação por nome e da IA)",
}


def coletar(conn) -> dict:
    params = {"sit": list(SITUACOES_OPERACIONAIS), "s": VIGENTE, "n": NAO_VIGENTE}
    resultado = {}
    for chave, sql in CONSULTAS.items():
        inicio = time.perf_counter()
        resultado[chave] = consultar(conn, sql, params)
        logger.info("consulta=%s linhas=%d ms=%d", chave, len(resultado[chave]),
                    (time.perf_counter() - inicio) * 1000)
    return resultado


def resumo(dados: dict) -> dict:
    lot = {linha["situacao"]: linha["viaturas"] for linha in dados["lotacao_operacional"]}
    total = sum(lot.values()) or 1
    problema = sum(v for k, v in lot.items() if not k.startswith("5."))
    invisiveis = sum(v for k, v in lot.items() if k.startswith(("1.", "2.")))
    return {
        "frota_operacional": total,
        "com_problema_de_lotacao": problema,
        "percentual_com_problema": round(100 * problema / total, 1),
        "invisiveis_no_cautela": invisiveis,
    }


def _tabela(linhas: list[dict]) -> str:
    if not linhas:
        return "_(nenhuma linha)_\n"
    colunas = list(linhas[0].keys())
    saida = ["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
    for linha in linhas:
        saida.append("| " + " | ".join("" if linha[c] is None else str(linha[c]) for c in colunas) + " |")
    return "\n".join(saida) + "\n"


def gerar_markdown(dados: dict, res: dict, quando: datetime) -> str:
    partes = [
        "# Diagnóstico da lotação de viaturas (banco de desenvolvimento)\n",
        f"Gerado em {quando:%d/%m/%Y %H:%M} por `avaliacao/diagnostico_real.py`. Conexão somente leitura; "
        "apenas contagens agregadas (nenhum nome, placa, chassi, RENAVAM, valor, contato ou log).\n",
        "## Resumo\n",
        f"- Frota operacional (situações {', '.join(map(str, SITUACOES_OPERACIONAIS))}): **{res['frota_operacional']}** viaturas",
        f"- Com problema de lotação: **{res['com_problema_de_lotacao']} ({res['percentual_com_problema']}%)**",
        f"- Invisíveis no Cautela (sem `cod_opm` ou `cod_opm` inexistente): **{res['invisiveis_no_cautela']}**",
        "- O Cautela filtra a grade do P4 por `tb_veiculo.cod_opm` e o check-in exige `opm.vigente = 'S'`.\n",
    ]
    for chave, titulo in TITULOS.items():
        partes.append(f"## {titulo}\n")
        partes.append(_tabela(dados[chave]))
    return "\n".join(partes)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", help="arquivo .env com DATABASE_URL (alternativa: DIAG_DATABASE_URL)")
    parser.add_argument("--saida", default=str(RAIZ / "evidencias"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        with conectar(carregar_url(args.env_file)) as conn:
            dados = coletar(conn)
    except ErroConexao as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 2

    quando = datetime.now()
    res = resumo(dados)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    base = saida / f"diagnostico_real_{quando:%Y%m%d_%H%M%S}"
    base.with_suffix(".md").write_text(gerar_markdown(dados, res, quando), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps({"gerado_em": quando.isoformat(), "resumo": res, "dados": dados}, ensure_ascii=False,
                   indent=2, default=str), encoding="utf-8")
    print(f"Frota operacional: {res['frota_operacional']} | com problema: {res['com_problema_de_lotacao']} "
          f"({res['percentual_com_problema']}%) | invisíveis no Cautela: {res['invisiveis_no_cautela']}")
    print(f"Relatório: {base.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
