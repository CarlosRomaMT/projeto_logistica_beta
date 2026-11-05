import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import carga, de_para, diagnostico, divergencias, opms, viaturas
from app.core.db import engine
from app.errors import ErroDominio
from app.services.de_para import sincronizar_de_para

logger = logging.getLogger("uvicorn.error")


def sincronizar_de_para_na_subida():
    """Deixa as sugestões de de-para prontas para o revisor (aba Implantação) desde a subida.

    Não altera viaturas nem decisões já gravadas. Uma falha aqui não impede a API de subir:
    o de-para ainda pode ser gerado pela carga ou pelo `scripts.de_para gerar`.
    """
    try:
        with engine.begin() as conn:
            criadas = sincronizar_de_para(conn)
        logger.info("De-para sincronizado na subida: %d unidade(s) antiga(s) nova(s).", criadas)
    except Exception:
        logger.exception("Falha ao sincronizar o de-para na subida; a API segue no ar.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    sincronizar_de_para_na_subida()
    yield


app = FastAPI(title="Sistema de Logística - Frota (MVP)", lifespan=lifespan)
app.include_router(opms.router)
app.include_router(viaturas.router)
app.include_router(diagnostico.router)
app.include_router(de_para.router)
app.include_router(divergencias.router)
app.include_router(carga.router)


@app.exception_handler(ErroDominio)
def tratar_erro_dominio(_: Request, erro: ErroDominio):
    return JSONResponse(status_code=erro.status_code, content={"detail": erro.mensagem})


@app.get("/health")
def health():
    return {"status": "ok"}
