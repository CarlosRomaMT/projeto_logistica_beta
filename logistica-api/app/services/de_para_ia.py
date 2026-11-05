"""IA no fluxo do de-para (Implantação, etapa 1): sugere a OPM das unidades antigas sem confirmação.

Camadas: nome igual após normalizar (confirmado na subida, sem IA) → Qwen local → semelhança de texto
(plano B, já gravada na subida). A IA só troca a SUGESTÃO de linhas PENDENTE ou SEM_CORRESPONDENCIA;
nunca confirma, nunca mexe em decisão humana e nunca move viatura. Quem confirma é o revisor, pelo
mesmo caminho validado de sempre (`confirmar_de_para` + serviço de movimentação).

As chamadas ao modelo levam segundos: nenhuma transação fica aberta durante elas. Cada resultado é
gravado numa transação curta que só altera a linha se ela continua aguardando decisão.
"""

import logging
from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import ID_OPM_CONTINGENCIA, STATUS_OPM_ATIVA
from app.core.db import engine
from app.services import ia_de_para as ia
from app.services.de_para import SITUACAO_PENDENTE, SITUACAO_SEM_CORRESPONDENCIA

logger = logging.getLogger("uvicorn.error")

AGUARDANDO = (SITUACAO_PENDENTE, SITUACAO_SEM_CORRESPONDENCIA)
FALHAS = (ia.INDISPONIVEL, ia.TIMEOUT)


def opms_candidatas(conn: Connection) -> list[ia.Candidata]:
    linhas = conn.execute(
        text("SELECT id_opm, nome, abreviatura FROM tb_opm"
             " WHERE status = :ativa AND id_opm <> :contingencia ORDER BY id_opm"),
        {"ativa": STATUS_OPM_ATIVA, "contingencia": ID_OPM_CONTINGENCIA},
    ).mappings()
    return [ia.Candidata(linha["id_opm"], linha["nome"], linha["abreviatura"]) for linha in linhas]


def registrar_execucao(conn: Connection, cd_unidade: str, modelo: str, r: ia.RespostaIA, usuario: str) -> None:
    conn.execute(
        text("""
            INSERT INTO tb_execucao_ia (cd_unidade_legado, modelo, resultado, motivo, id_opm, confianca,
                                        latencia_ms, usuario)
            VALUES (:cd, :modelo, :resultado, :motivo, :opm, :confianca, :latencia, :usuario)
        """),
        {"cd": cd_unidade, "modelo": modelo, "resultado": r.resultado, "motivo": r.motivo, "opm": r.id_opm,
         "confianca": r.confianca, "latencia": r.latencia_ms, "usuario": usuario},
    )


def _observacao(alvo: dict, r: ia.RespostaIA) -> str | None:
    """Quando a IA substitui uma sugestão por semelhança, guarda a opinião anterior para o revisor."""
    if alvo["metodo"] != "SIMILARIDADE" or alvo["fk_id_opm"] is None:
        return alvo["observacao"] if alvo["metodo"] == "IA" else None
    if alvo["fk_id_opm"] == r.id_opm:
        return "IA e semelhança de nome indicam a mesma OPM."
    return f"A semelhança de nome indicava: {alvo['nome_opm']} ({round(float(alvo['score'] or 0) * 100)}%)."[:200]


def gravar_resultado(conn: Connection, alvo: dict, r: ia.RespostaIA, modelo: str) -> bool:
    """Grava a análise da IA na linha do de-para. Devolve False se a linha já foi decidida."""
    params = {"cd": alvo["cd_unidade_legado"], "aguardando": list(AGUARDANDO), "resultado": r.resultado,
              "ia_opm": r.id_opm if r.resultado in (ia.ACEITA, ia.BAIXA_CONFIANCA) else None,
              "confianca": r.confianca, "modelo": modelo,
              "justificativa": r.justificativa if r.resultado != ia.DESCARTADA else f"Resposta descartada: {r.motivo}"}
    campos_ia = """ia_resultado = :resultado, ia_id_opm = :ia_opm, ia_confianca = :confianca,
                   ia_justificativa = :justificativa, ia_modelo = :modelo, dt_ia = now(), dt_atualizacao = now()"""
    if r.resultado == ia.ACEITA:
        sql = f"""UPDATE tb_de_para_unidade
                  SET fk_id_opm = :ia_opm, situacao = :pendente, metodo = 'IA', score = :confianca,
                      observacao = :observacao, {campos_ia}
                  WHERE cd_unidade_legado = :cd AND situacao = ANY(:aguardando)"""
        params.update(pendente=SITUACAO_PENDENTE, observacao=_observacao(alvo, r))
    else:
        # Sem sugestão nova: a da semelhança (se houver) continua valendo; só registra o parecer da IA.
        sql = f"""UPDATE tb_de_para_unidade SET {campos_ia}
                  WHERE cd_unidade_legado = :cd AND situacao = ANY(:aguardando)"""
    return conn.execute(text(sql), params).rowcount > 0


def _mensagem(cont: Counter, total: int, modelo: str, parou_no_meio: bool) -> str:
    if total == 0:
        return "Nenhuma unidade aguardando sugestão: nada para a IA analisar."
    falhas = sum(cont[f] for f in FALHAS)
    if falhas == total:
        return (f"IA indisponível ({modelo}): nenhuma sugestão nova. As sugestões por semelhança de nome "
                "continuam valendo e você pode escolher a OPM manualmente.")
    partes = [f"A IA analisou {total - falhas} unidade(s): {cont[ia.ACEITA]} sugestão(ões) nova(s)"]
    if cont[ia.SEM_CORRESPONDENCIA] + cont[ia.BAIXA_CONFIANCA]:
        partes.append(f"{cont[ia.SEM_CORRESPONDENCIA] + cont[ia.BAIXA_CONFIANCA]} sem correspondência segura")
    if cont[ia.DESCARTADA]:
        partes.append(f"{cont[ia.DESCARTADA]} resposta(s) descartada(s) pela validação")
    texto = ", ".join(partes) + ". Confira e confirme cada sugestão."
    if parou_no_meio or falhas:
        texto += f" A IA não respondeu para {falhas} unidade(s); elas ficaram com a sugestão por semelhança."
    return texto


def exemplos_confirmados(conn: Connection) -> list[ia.Exemplo]:
    """RAG: associações JÁ CONFIRMADAS (nome idêntico ou decisão humana) para OPM ativa. Sugestões
    pendentes nunca viram exemplo, e cada confirmação nova melhora as sugestões seguintes."""
    linhas = conn.execute(
        text("""
            SELECT d.cd_unidade_legado, d.ds_unidade_legado, o.nome
            FROM tb_de_para_unidade d JOIN tb_opm o ON o.id_opm = d.fk_id_opm
            WHERE d.situacao = 'CONFIRMADO' AND o.status = :ativa AND o.id_opm <> :contingencia
            ORDER BY d.cd_unidade_legado
        """),
        {"ativa": STATUS_OPM_ATIVA, "contingencia": ID_OPM_CONTINGENCIA},
    ).mappings()
    return [ia.Exemplo(linha["cd_unidade_legado"], linha["ds_unidade_legado"], linha["nome"]) for linha in linhas]


def sugerir_com_ia(cliente: ia.ClienteOllama, usuario: str) -> dict:
    with engine.connect() as conn:
        alvos = [dict(linha) for linha in conn.execute(
            text("""
                SELECT d.cd_unidade_legado, d.ds_unidade_legado, d.fk_id_opm, d.metodo, d.score,
                       d.observacao, o.nome AS nome_opm
                FROM tb_de_para_unidade d LEFT JOIN tb_opm o ON o.id_opm = d.fk_id_opm
                WHERE d.situacao = ANY(:aguardando) ORDER BY d.cd_unidade_legado
            """),
            {"aguardando": list(AGUARDANDO)},
        ).mappings()]
        seletor = ia.SeletorCandidatas(opms_candidatas(conn))
        banco = None
        if getattr(cliente, "usa_exemplos", False):
            confirmados = exemplos_confirmados(conn)
            if len(confirmados) >= ia.IA_MIN_EXEMPLOS_RAG:
                banco = ia.BancoExemplos(confirmados)
            else:
                logger.info("RAG desligado: %d associação(ões) confirmada(s), mínimo %d para usar exemplos.",
                            len(confirmados), ia.IA_MIN_EXEMPLOS_RAG)

    identificacao = getattr(cliente, "identificacao", cliente.modelo)
    cont: Counter = Counter()
    for alvo in alvos:
        descricao = alvo["ds_unidade_legado"]
        candidatas = seletor.selecionar(descricao)
        if banco is not None:
            exemplos = banco.buscar(descricao, excluir_chave=alvo["cd_unidade_legado"])
            r = cliente.sugerir(descricao, candidatas, exemplos)
        else:
            r = cliente.sugerir(descricao, candidatas)
        cont[r.resultado] += 1
        # Registra a versão de prompt realmente usada (ex.: v6 sem exemplos suficientes roda como v2).
        usada = f"{cliente.modelo} (prompt {r.versao_prompt})" if getattr(r, "versao_prompt", None) else identificacao
        with engine.begin() as conn:
            registrar_execucao(conn, alvo["cd_unidade_legado"], usada, r, usuario)
            if r.resultado not in FALHAS and not gravar_resultado(conn, alvo, r, usada):
                cont["ja_decididas"] += 1  # o revisor confirmou enquanto a IA pensava: decisão humana vale

    logger.info("IA no de-para por %s: %s", usuario, dict(cont))
    falhas = sum(cont[f] for f in FALHAS)
    return {
        "modelo": cliente.modelo,
        "analisadas": len(alvos),
        "sugestoes_novas": cont[ia.ACEITA],
        "sem_correspondencia": cont[ia.SEM_CORRESPONDENCIA] + cont[ia.BAIXA_CONFIANCA],
        "descartadas": cont[ia.DESCARTADA],
        "falhas": falhas,
        "ia_disponivel": not alvos or falhas < len(alvos),
        "mensagem": _mensagem(cont, len(alvos), cliente.modelo, cliente.desligado),
    }


def listar_execucoes(limite: int = 50) -> list[dict]:
    with engine.connect() as conn:
        return [dict(linha) for linha in conn.execute(
            text("""SELECT id, cd_unidade_legado, modelo, resultado, motivo, id_opm, confianca, latencia_ms,
                           usuario, dt_execucao
                    FROM tb_execucao_ia ORDER BY id DESC LIMIT :limite"""),
            {"limite": limite},
        ).mappings()]
