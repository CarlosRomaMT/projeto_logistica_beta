from fastapi import APIRouter

from app.core.db import engine
from app.schemas import ConfirmacaoDeParaIn, ConfirmacaoDeParaOut, DeParaOut
from app.services.de_para import (
    aplicar_de_para_na_contingencia,
    buscar_de_para,
    confirmar_de_para,
    listar_de_para,
)

# Aba Implantação: mostra descrições do cadastro antigo. Em produção, só para perfil autorizado.
router = APIRouter(prefix="/api/de-para", tags=["Implantação, etapa 1: de-para"])


@router.get("", response_model=list[DeParaOut])
def listar():
    return listar_de_para()


@router.post("/{cd_unidade}/confirmar", response_model=ConfirmacaoDeParaOut)
def confirmar(cd_unidade: str, dados: ConfirmacaoDeParaIn):
    """Confirma a OPM da unidade antiga e tira da contingência as viaturas dela (mesma transação)."""
    with engine.begin() as conn:
        anterior = confirmar_de_para(conn, cd_unidade, dados.id_opm, dados.usuario)
        resultado = aplicar_de_para_na_contingencia(conn, cd_unidade, dados.usuario, anterior)
        return {"de_para": buscar_de_para(conn, cd_unidade), **resultado}
