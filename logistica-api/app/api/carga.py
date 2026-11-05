import logging

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.errors import RelatorioNaoEncontrado
from app.schemas import CargaIn, ConfirmacaoDeParaIn, ResultadoCargaOut, SituacaoCargaOut, ViaturaOut, ViaturaSemOpmOut
from app.services.carga import (
    ResultadoMigracao,
    caminho_relatorio,
    contar_aguardando_carga,
    executar_migracao,
    listar_sem_opm,
    lotar_da_contingencia,
)

logger = logging.getLogger("uvicorn.error")

# Carga em lote (RF04) pela tela. Em produção, só para perfil de administrador da implantação.
router = APIRouter(prefix="/api/carga", tags=["Implantação, etapa 2: carga da lotação"])


def _resposta(resultado: ResultadoMigracao, simulacao: bool) -> dict:
    return {
        "simulacao": simulacao,
        "atualizadas": resultado.atualizadas,
        "contingencia": resultado.contingencia,
        "de_para_criados": resultado.de_para_criados,
        "propostas_criadas": resultado.propostas_criadas,
        "lotadas": resultado.lotadas,
        "inconformidades": resultado.inconformidades,
        "relatorio": resultado.relatorio.name if resultado.relatorio else None,
    }


@router.get("", response_model=SituacaoCargaOut)
def situacao():
    return {"aguardando_carga": contar_aguardando_carga()}


@router.post("/simular", response_model=ResultadoCargaOut)
def simular():
    """Mesmo que o --dry-run: calcula tudo e desfaz, sem gravar relatório."""
    return _resposta(executar_migracao(dry_run=True), simulacao=True)


@router.post("/executar", response_model=ResultadoCargaOut)
def executar(dados: CargaIn):
    """Grava a lotação numa única transação e o relatório de inconformidades (com quem executou)."""
    resultado = executar_migracao(executado_por=dados.usuario)
    logger.info("Carga da lotação executada por %s: %d viatura(s) alterada(s).", dados.usuario, resultado.atualizadas)
    return _resposta(resultado, simulacao=False)


@router.get("/sem-opm", response_model=list[ViaturaSemOpmOut])
def sem_opm():
    """Etapa 4: viaturas que ficaram na OPM 0, com o motivo e a OPM sugerida."""
    return listar_sem_opm()


@router.post("/sem-opm/{id_viatura}/lotar", response_model=ViaturaOut)
def lotar(id_viatura: int, dados: ConfirmacaoDeParaIn):
    """Etapa 4: lota uma viatura da OPM 0; na implantação, cautelada também pode ser lotada."""
    return lotar_da_contingencia(id_viatura, dados.id_opm, dados.usuario)


@router.get("/relatorios/{nome}")
def baixar_relatorio(nome: str):
    caminho = caminho_relatorio(nome)
    if caminho is None:
        raise RelatorioNaoEncontrado(nome)
    return FileResponse(caminho, media_type="text/csv", filename=nome)
