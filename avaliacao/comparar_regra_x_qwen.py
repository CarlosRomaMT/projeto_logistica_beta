"""Comparativo regra atual x Qwen (Ollama local) x híbrido sobre o gabarito real.

Não acessa o banco: lê os CSVs de `gerar_gabarito` e só usa os NOMES (o gabarito veio dos códigos).
Os nomes vão apenas para o Ollama local; nada sai da máquina.

    python -m avaliacao.comparar_regra_x_qwen [--limite 30] [--sem-ia] [--modelo qwen2.5:7b]

Saídas:
    evidencias/comparativo_<data>.md e .json   (só métricas agregadas)
    dados_reais/comparativo_detalhe_<data>.csv (linha a linha, com nomes; fora do git)
"""

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "logistica-api"))

from app.services import ia_de_para as ia  # noqa: E402
from app.services.de_para import LIMIAR_SUGESTAO, sugerir_opm  # noqa: E402

from avaliacao.gerar_gabarito import ARQ_GABARITO, ARQ_OPMS, gravar_csv, ler_csv  # noqa: E402
from avaliacao.metricas import HIBRIDO, QWEN, REGRA, calcular, sugestao_hibrido  # noqa: E402

logger = logging.getLogger("comparativo")


def avaliar(gabarito: list[dict], opms: list[dict], cliente: "ia.ClienteOllama | None",
            n_candidatas: int) -> list[dict]:
    opms_regra = [{"id_opm": int(o["cod_opm"]), "nome": o["opm"]} for o in opms]
    candidatas_todas = [ia.Candidata(int(o["cod_opm"]), o["opm"], o["opm_abreviatura"] or None) for o in opms]
    seletor = ia.SeletorCandidatas(candidatas_todas)

    linhas = []
    inicio = time.perf_counter()
    for n, item in enumerate(gabarito, 1):
        descricao, alvo = item["descricao_upm"], int(item["cod_opm_gabarito"])
        regra = sugerir_opm(descricao, opms_regra)
        candidatas = seletor.selecionar(descricao, n_candidatas)
        ids = [c.id_opm for c in candidatas]
        linha = {
            "cod_upm": int(item["cod_upm"]),
            "descricao_upm": descricao,
            "gabarito": alvo,
            "regra_situacao": regra.situacao,
            "regra_id": regra.id_opm,
            "regra_score": regra.score,
            "gabarito_nas_candidatas": alvo in ids,
            "posicao_gabarito": ids.index(alvo) + 1 if alvo in ids else None,
        }
        if cliente is not None:
            r = cliente.sugerir(descricao, candidatas)
            linha.update({"ia_resultado": r.resultado, "ia_motivo": r.motivo, "ia_id": r.id_opm,
                          "ia_confianca": r.confianca, "ia_justificativa": r.justificativa,
                          "ia_latencia_ms": r.latencia_ms})
            linha["hibrido_id"], linha["hibrido_origem"] = sugestao_hibrido(linha)
        linhas.append(linha)
        if n % 10 == 0 or n == len(gabarito):
            logger.info("progresso %d/%d (%.0f s)", n, len(gabarito), time.perf_counter() - inicio)
    return linhas


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def gerar_markdown(m: dict, meta: dict) -> str:
    metodos = [(REGRA, "Regra atual (normalização + difflib)")]
    if QWEN in m:
        metodos += [(QWEN, f"Qwen ({meta['modelo']}) sozinho"), (HIBRIDO, "Híbrido: exata → Qwen → semelhança")]
    p = [
        "# Comparativo: regra atual x Qwen local x híbrido\n",
        f"Gerado em {meta['gerado_em']} por `avaliacao/comparar_regra_x_qwen.py`.\n",
        f"- Gabarito: **{meta['total']}** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos "
        f"(pureza ≥ {meta['pureza_minima']}, OPM vigente).",
        f"- Candidatas por pergunta à IA: {meta['candidatas']} (de {meta['opms_vigentes']} OPMs vigentes); "
        f"confiança mínima {meta['confianca_minima']}; limiar de semelhança da regra {LIMIAR_SUGESTAO}.",
        "- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.\n",
        "## Resultado\n",
        "| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for chave, nome in metodos:
        s = m[chave]
        p.append(f"| {nome} | {s['acertos']} | {s['erros']} | {s['sem_sugestao']} | {_pct(s['acuracia'])} | "
                 f"{_pct(s['precisao'])} | {_pct(s['cobertura'])} |")
    r = m[REGRA]
    p += ["", "## Segurança da regra atual\n",
          f"- Confirmações automáticas (nome igual após normalizar): **{r['confirmacoes_automaticas']}**, "
          f"das quais **{r['confirmacoes_automaticas_erradas']} erradas**.",
          f"- Situações: `{json.dumps(r['por_situacao'], ensure_ascii=False)}`"]
    if QWEN in m:
        q, g = m[QWEN], m["ganho_do_hibrido"]
        p += ["", "## IA (Qwen)\n",
              f"- Resultados: `{json.dumps(q['por_resultado'], ensure_ascii=False)}`",
              f"- Motivos de descarte/falha: `{json.dumps(q['motivos_descarte'], ensure_ascii=False)}`",
              f"- Latência por unidade: média {q['latencia_ms_media']} ms, mediana {q['latencia_ms_mediana']} ms, "
              f"p95 {q['latencia_ms_p95']} ms",
              f"- OPM correta entre as candidatas enviadas: **{_pct(q['gabarito_nas_candidatas'])}** "
              "(teto da IA: se a certa não foi enviada, não há como acertar)",
              f"- Acurácia do Qwen quando a OPM correta foi enviada: **{_pct(q['acuracia_quando_gabarito_enviado'])}**",
              "", "## Onde a IA agrega\n",
              f"- Casos que a regra atual não acertava: {g['casos_que_a_regra_nao_acertava']}",
              f"- Resolvidos pelo híbrido: **{g['resolvidos_pelo_hibrido']}**",
              f"- Acertos da regra perdidos no híbrido: {g['acertos_da_regra_perdidos_no_hibrido']}",
              f"- Origem das sugestões do híbrido: `{json.dumps(m[HIBRIDO]['origem'], ensure_ascii=False)}`"]
    p += ["", "Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; "
          "só a igualdade exata do nome é confirmada automaticamente.\n"]
    return "\n".join(p)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dados", default=str(RAIZ / "dados_reais"))
    parser.add_argument("--saida", default=str(RAIZ / "evidencias"))
    parser.add_argument("--limite", type=int, help="avalia só uma amostra aleatória de N UPMs")
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--sem-ia", action="store_true", help="só a regra atual (não chama o Ollama)")
    parser.add_argument("--modelo", default=ia.OLLAMA_MODELO)
    parser.add_argument("--ollama-url", default=ia.OLLAMA_URL)
    parser.add_argument("--candidatas", type=int, default=ia.IA_MAX_CANDIDATAS)
    parser.add_argument("--confianca-minima", type=float, default=ia.IA_CONFIANCA_MINIMA)
    parser.add_argument("--timeout", type=float, default=ia.IA_TIMEOUT_S)
    parser.add_argument("--pureza-minima", default="1.0", help="só para constar no relatório")
    parser.add_argument("--rotulo", default="", help="sufixo do nome do relatório (ex.: falha_ollama)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    dados = Path(args.dados)
    try:
        gabarito, opms = ler_csv(dados / ARQ_GABARITO), ler_csv(dados / ARQ_OPMS)
    except FileNotFoundError:
        print(f"ERRO: gabarito não encontrado em {dados}. Rode antes: python -m avaliacao.gerar_gabarito",
              file=sys.stderr)
        return 2
    if args.limite and args.limite < len(gabarito):
        gabarito = random.Random(args.semente).sample(gabarito, args.limite)

    cliente = None if args.sem_ia else ia.ClienteOllama(
        url=args.ollama_url, modelo=args.modelo, timeout_s=args.timeout, confianca_minima=args.confianca_minima)
    linhas = avaliar(gabarito, opms, cliente, args.candidatas)
    if cliente is not None and cliente.desligado:
        logger.warning("O Ollama ficou indisponível durante a execução: o híbrido caiu na regra atual.")

    metricas = calcular(linhas, ia_executada=cliente is not None)
    quando = datetime.now()
    meta = {"gerado_em": f"{quando:%d/%m/%Y %H:%M}", "total": len(linhas), "modelo": args.modelo,
            "candidatas": args.candidatas, "opms_vigentes": len(opms), "confianca_minima": args.confianca_minima,
            "pureza_minima": args.pureza_minima, "amostra": args.limite, "semente": args.semente}

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    sufixo = f"_{args.rotulo}" if args.rotulo else ""
    base = saida / f"comparativo_{quando:%Y%m%d_%H%M%S}{sufixo}"
    base.with_suffix(".md").write_text(gerar_markdown(metricas, meta), encoding="utf-8")
    base.with_suffix(".json").write_text(json.dumps({"meta": meta, "metricas": metricas}, ensure_ascii=False,
                                                    indent=2), encoding="utf-8")
    detalhe = dados / f"comparativo_detalhe_{quando:%Y%m%d_%H%M%S}.csv"
    gravar_csv(detalhe, linhas)

    for chave in (REGRA, QWEN, HIBRIDO):
        if chave in metricas:
            s = metricas[chave]
            print(f"{chave:12s} acertos={s['acertos']:4d} erros={s['erros']:4d} sem_sugestao={s['sem_sugestao']:4d} "
                  f"acuracia={_pct(s['acuracia'])} precisao={_pct(s['precisao'])}")
    print(f"Relatório: {base.with_suffix('.md')}")
    print(f"Detalhe (fora do git): {detalhe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
