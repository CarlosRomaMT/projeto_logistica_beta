from fastapi import APIRouter

from app.schemas import DecisaoPropostasIn, PropostaCorrecaoOut
from app.services import divergencias

router = APIRouter(prefix="/api/divergencias", tags=["Implantação, etapa 3: divergências"])


@router.get("", response_model=list[PropostaCorrecaoOut])
def listar():
    return divergencias.listar_propostas()


@router.post("/procurar")
def procurar():
    """Cria propostas para viaturas nunca movimentadas cuja coluna nova diverge do legado."""
    return {"criadas": divergencias.procurar_divergencias()}


@router.post("/aplicar")
def aplicar(dados: DecisaoPropostasIn):
    """Aplica o lote aprovado pelo serviço de movimentação. Tudo ou nada."""
    return {"aplicadas": divergencias.aplicar_propostas(dados.ids, dados.usuario)}


@router.post("/rejeitar")
def rejeitar(dados: DecisaoPropostasIn):
    return {"rejeitadas": divergencias.rejeitar_propostas(dados.ids, dados.usuario)}
