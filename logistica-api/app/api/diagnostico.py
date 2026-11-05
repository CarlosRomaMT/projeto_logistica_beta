from fastapi import APIRouter

from app.schemas import LegadoViaturaOut
from app.services.diagnostico import listar_legado_das_viaturas

router = APIRouter(prefix="/api/diagnostico", tags=["Diagnóstico (demonstração)"])


@router.get("/legado", response_model=list[LegadoViaturaOut])
def legado():
    """Unidade do cadastro antigo e situação do de-para de cada viatura."""
    return listar_legado_das_viaturas()
