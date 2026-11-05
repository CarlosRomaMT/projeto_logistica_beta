from fastapi import APIRouter

from app.schemas import OpmOut
from app.services.opms import buscar_opms

router = APIRouter(prefix="/api/opms", tags=["OPMs"])


@router.get("", response_model=list[OpmOut])
def listar(q: str = "", incluir_inativas: bool = False):
    """`incluir_inativas` existe só para demonstrar o bloqueio do RF03."""
    return buscar_opms(q, incluir_inativas)
