"""Métricas do comparativo regra atual x Qwen x híbrido (funções puras, testáveis)."""

from collections import Counter
from statistics import mean, median

REGRA = "regra_atual"
QWEN = "qwen"
HIBRIDO = "hibrido"


def sugestao_regra(linha: dict) -> int | None:
    return linha["regra_id"] if linha["regra_situacao"] in ("CONFIRMADO", "PENDENTE") else None


def sugestao_qwen(linha: dict) -> int | None:
    return linha["ia_id"] if linha["ia_resultado"] == "ACEITA" else None


def sugestao_hibrido(linha: dict) -> tuple[int | None, str]:
    """Regra exata primeiro (sem IA); depois a IA validada; por último a semelhança da regra."""
    if linha["regra_situacao"] == "CONFIRMADO":
        return linha["regra_id"], "regra_exata"
    if (ia := sugestao_qwen(linha)) is not None:
        return ia, "qwen"
    if linha["regra_situacao"] == "PENDENTE":
        return linha["regra_id"], "regra_similaridade"
    return None, "sem_sugestao"


def placar(sugestoes: list[int | None], gabarito: list[int]) -> dict:
    total = len(gabarito)
    acertos = sum(1 for s, g in zip(sugestoes, gabarito) if s is not None and s == g)
    erros = sum(1 for s, g in zip(sugestoes, gabarito) if s is not None and s != g)
    sugeridas = acertos + erros
    return {
        "total": total,
        "acertos": acertos,
        "erros": erros,
        "sem_sugestao": total - sugeridas,
        "acuracia": round(acertos / total, 3) if total else 0.0,
        "precisao": round(acertos / sugeridas, 3) if sugeridas else 0.0,
        "cobertura": round(sugeridas / total, 3) if total else 0.0,
    }


def _percentil(valores: list[int], p: float) -> int:
    if not valores:
        return 0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p * (len(ordenados) - 1))))]


def calcular(linhas: list[dict], ia_executada: bool = True) -> dict:
    gabarito = [linha["gabarito"] for linha in linhas]
    regra = [sugestao_regra(linha) for linha in linhas]
    resultado = {REGRA: placar(regra, gabarito)}

    confirmadas = [linha for linha in linhas if linha["regra_situacao"] == "CONFIRMADO"]
    resultado[REGRA]["confirmacoes_automaticas"] = len(confirmadas)
    resultado[REGRA]["confirmacoes_automaticas_erradas"] = sum(
        1 for linha in confirmadas if linha["regra_id"] != linha["gabarito"])
    resultado[REGRA]["por_situacao"] = dict(Counter(linha["regra_situacao"] for linha in linhas))

    if not ia_executada:
        return resultado

    qwen = [sugestao_qwen(linha) for linha in linhas]
    hibrido = [sugestao_hibrido(linha) for linha in linhas]
    resultado[QWEN] = placar(qwen, gabarito)
    resultado[HIBRIDO] = placar([h for h, _ in hibrido], gabarito)
    resultado[HIBRIDO]["origem"] = dict(Counter(origem for _, origem in hibrido))

    latencias = [linha["ia_latencia_ms"] for linha in linhas if linha["ia_resultado"] not in ("INDISPONIVEL",)]
    no_top = [linha for linha in linhas if linha["gabarito_nas_candidatas"]]
    resultado[QWEN].update({
        "por_resultado": dict(Counter(linha["ia_resultado"] for linha in linhas)),
        "motivos_descarte": dict(Counter(linha["ia_motivo"] for linha in linhas if linha["ia_motivo"])),
        "latencia_ms_media": int(mean(latencias)) if latencias else 0,
        "latencia_ms_mediana": int(median(latencias)) if latencias else 0,
        "latencia_ms_p95": _percentil(latencias, 0.95),
        # Teto da IA: se a OPM certa não foi enviada, o modelo não tem como acertar.
        "gabarito_nas_candidatas": round(len(no_top) / len(linhas), 3) if linhas else 0.0,
        "acuracia_quando_gabarito_enviado": round(
            sum(1 for linha in no_top if sugestao_qwen(linha) == linha["gabarito"]) / len(no_top), 3) if no_top else 0.0,
    })

    # Alerta de coerência (determinístico): em quantas sugestões aceitas ele aparece e se pegou erros.
    if any("ia_alerta" in linha for linha in linhas):
        aceitas = [linha for linha in linhas if linha["ia_resultado"] == "ACEITA"]
        resultado[QWEN]["alertas_em_erros"] = sum(
            1 for linha in aceitas if linha.get("ia_alerta") and linha["ia_id"] != linha["gabarito"])
        resultado[QWEN]["alertas_em_acertos"] = sum(
            1 for linha in aceitas if linha.get("ia_alerta") and linha["ia_id"] == linha["gabarito"])

    # Top 3 na dúvida: a OPM certa está entre as opções mostradas ao revisor?
    if any("opcoes_mostradas" in linha for linha in linhas):
        def mostradas(linha):
            return {int(i) for i in str(linha.get("opcoes_mostradas") or "").split()}
        resultado[QWEN]["certa_entre_opcoes_mostradas"] = round(
            sum(1 for linha in linhas if int(linha["gabarito"]) in mostradas(linha)) / len(linhas), 3) if linhas else 0.0
        resultado[QWEN]["linhas_com_alternativas"] = sum(
            1 for linha in linhas if len(mostradas(linha)) > (1 if linha["ia_resultado"] == "ACEITA" else 0))

    # Onde a IA agrega: casos que a regra atual não acertava.
    regra_errava = [i for i, linha in enumerate(linhas) if regra[i] != linha["gabarito"]]
    resultado["ganho_do_hibrido"] = {
        "casos_que_a_regra_nao_acertava": len(regra_errava),
        "resolvidos_pelo_hibrido": sum(1 for i in regra_errava if hibrido[i][0] == gabarito[i]),
        "acertos_da_regra_perdidos_no_hibrido": sum(
            1 for i, linha in enumerate(linhas) if regra[i] == linha["gabarito"] and hibrido[i][0] != linha["gabarito"]),
    }
    return resultado
