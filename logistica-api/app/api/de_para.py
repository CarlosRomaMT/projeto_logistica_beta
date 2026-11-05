from collections.abc import Iterator

from fastapi import APIRouter, Depends

from app.core.db import engine
from app.schemas import (
    ConfirmacaoDeParaIn,
    ConfirmacaoHistoricoOut,
    ConfirmacaoDeParaOut,
    DeParaOut,
    ExecucaoIaOut,
    ResultadoSugestaoIaOut,
    StatusIaOut,
    SugestaoIaIn,
)
from app.services import ia_de_para as ia
from app.services.de_para import (
    aplicar_de_para_na_contingencia,
    buscar_de_para,
    confirmar_de_para,
    confirmar_sugestoes_do_historico,
    listar_de_para,
)
from app.services.de_para_ia import listar_execucoes, sugerir_com_ia

# Aba Implantação: mostra descrições do cadastro antigo. Em produção, só para perfil autorizado.
router = APIRouter(prefix="/api/de-para", tags=["Implantação, etapa 1: de-para"])

MSG_IA_DESATIVADA = "IA desativada na configuração (IA_HABILITADA=false): use as sugestões por semelhança."


def obter_cliente_ia() -> Iterator[ia.ClienteOllama | None]:
    """Um cliente por requisição (o disjuntor vale para o lote). Substituído nos testes."""
    if not ia.IA_HABILITADA:
        yield None
        return
    cliente = ia.ClienteOllama()
    try:
        yield cliente
    finally:
        cliente.fechar()


@router.get("", response_model=list[DeParaOut])
def listar():
    return listar_de_para()


# Declarada antes de /{cd_unidade}/confirmar para "historico" não ser lido como código de unidade.
@router.post("/historico/confirmar", response_model=ConfirmacaoHistoricoOut)
def confirmar_historico(dados: SugestaoIaIn):
    """Revisor confirma de uma vez as sugestões pelo histórico das viaturas (tudo ou nada)."""
    with engine.begin() as conn:
        confirmadas = confirmar_sugestoes_do_historico(conn, dados.usuario)
    return {"confirmadas": [c["cd_unidade_legado"] for c in confirmadas],
            "movidas": [placa for c in confirmadas for placa in c["movidas"]],
            "bloqueadas": [b for c in confirmadas for b in c["bloqueadas"]]}


@router.post("/{cd_unidade}/confirmar", response_model=ConfirmacaoDeParaOut)
def confirmar(cd_unidade: str, dados: ConfirmacaoDeParaIn):
    """Confirma a OPM da unidade antiga e tira da contingência as viaturas dela (mesma transação)."""
    with engine.begin() as conn:
        anterior = confirmar_de_para(conn, cd_unidade, dados.id_opm, dados.usuario)
        resultado = aplicar_de_para_na_contingencia(conn, cd_unidade, dados.usuario, anterior)
        return {"de_para": buscar_de_para(conn, cd_unidade), **resultado}


@router.get("/ia/status", response_model=StatusIaOut)
def status_ia(cliente: ia.ClienteOllama | None = Depends(obter_cliente_ia)):
    """A IA (Ollama + Qwen local) está pronta? Usado pelo aviso da tela; não gera texto."""
    if cliente is None:
        return {"habilitada": False, "disponivel": False, "modelo": ia.OLLAMA_MODELO, "motivo": MSG_IA_DESATIVADA}
    return {"habilitada": True, "modelo": cliente.modelo, **cliente.verificar()}


@router.post("/ia/sugerir", response_model=ResultadoSugestaoIaOut)
def sugerir_ia(dados: SugestaoIaIn, cliente: ia.ClienteOllama | None = Depends(obter_cliente_ia)):
    """Pede à IA sugestões para as unidades que aguardam decisão. Não confirma nem move viatura."""
    if cliente is None:
        return {"modelo": ia.OLLAMA_MODELO, "analisadas": 0, "sugestoes_novas": 0, "sem_correspondencia": 0,
                "descartadas": 0, "falhas": 0, "ia_disponivel": False, "mensagem": MSG_IA_DESATIVADA}
    return sugerir_com_ia(cliente, dados.usuario)


@router.get("/ia/execucoes", response_model=list[ExecucaoIaOut])
def execucoes_ia(limite: int = 50):
    """Registro das chamadas à IA (observabilidade): resultado, motivo de descarte e latência."""
    return listar_execucoes(min(max(limite, 1), 500))
