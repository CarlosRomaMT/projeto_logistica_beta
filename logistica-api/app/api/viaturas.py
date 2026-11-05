from fastapi import APIRouter

from app.schemas import MovimentacaoIn, ViaturaIn, ViaturaOut
from app.services import movimentacao

router = APIRouter(prefix="/api/viaturas", tags=["Viaturas"])


@router.get("", response_model=list[ViaturaOut])
def listar():
    return movimentacao.listar_viaturas()


@router.post("", response_model=ViaturaOut, status_code=201)
def criar(dados: ViaturaIn):
    return movimentacao.criar_viatura(dados.placa.upper(), dados.modelo, dados.id_opm, dados.usuario)


@router.post("/{id_viatura}/movimentar", response_model=ViaturaOut)
def movimentar(id_viatura: int, dados: MovimentacaoIn):
    return movimentacao.mover_viatura(id_viatura, dados.id_opm_destino, dados.usuario)
