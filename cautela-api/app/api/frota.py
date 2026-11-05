from fastapi import APIRouter, Header, HTTPException, Response

from app.repositories import frota

router = APIRouter(prefix="/api", tags=["Frota"])


@router.get("/p4")
def listar_p4():
    """Apoio à demonstração: lista os P4 fictícios para simular o login."""
    return frota.listar_p4()


@router.get("/frota/disponivel")
def frota_disponivel(response: Response, x_usuario_p4: str | None = Header(default=None)):
    # No MVP o P4 "autenticado" chega no cabeçalho X-Usuario-P4; em produção vem do SSO/token.
    p4 = frota.buscar_p4(x_usuario_p4) if x_usuario_p4 else None
    if p4 is None:
        raise HTTPException(status_code=401, detail="P4 não identificado.")
    response.headers["Cache-Control"] = "no-store"
    return {"p4": p4, "viaturas": frota.listar_disponiveis_para_p4(p4["login"])}
