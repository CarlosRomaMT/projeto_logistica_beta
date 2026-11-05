from datetime import datetime

from pydantic import BaseModel, Field


class OpmOut(BaseModel):
    id_opm: int
    nome: str
    status: str


class ViaturaOut(BaseModel):
    """Não expõe cd_unidade_legado (RNF02)."""

    id_viatura: int
    placa: str
    modelo: str
    status_operacional: str
    id_opm: int | None
    nome_opm: str | None


class LegadoViaturaOut(BaseModel):
    """Só para o endpoint de diagnóstico."""

    id_viatura: int
    cd_unidade_legado: str | None
    ds_unidade_legado: str | None
    situacao_de_para: str | None
    id_opm_de_para: int | None
    nome_opm_de_para: str | None
    score: float | None


class MovimentacaoIn(BaseModel):
    # Opcional de propósito: a ausência é tratada pela regra do RF03, com a mensagem oficial.
    id_opm_destino: int | None = None
    usuario: str = "demo.logistica"


class DeParaOut(BaseModel):
    cd_unidade_legado: str
    ds_unidade_legado: str
    situacao: str
    metodo: str | None
    score: float | None
    id_opm: int | None
    nome_opm: str | None
    observacao: str | None
    confirmado_por: str | None
    dt_confirmacao: datetime | None
    status_opm: str | None
    qtd_viaturas_contingencia: int


class ConfirmacaoDeParaIn(BaseModel):
    id_opm: int | None = None
    # Sem login real no MVP: quem decide se identifica. Em produção vem do SSO.
    usuario: str = Field(min_length=3, max_length=60)


class BloqueioOut(BaseModel):
    placa: str
    status: str


class ConfirmacaoDeParaOut(BaseModel):
    de_para: DeParaOut
    movidas: list[str]
    bloqueadas: list[BloqueioOut]


class PropostaCorrecaoOut(BaseModel):
    id: int
    id_viatura: int
    placa: str
    modelo: str
    status_operacional: str
    cd_unidade_legado: str | None
    ds_unidade_legado: str | None
    id_opm_atual: int
    nome_opm_atual: str
    id_opm_proposta: int
    nome_opm_proposta: str
    situacao: str
    bloqueio: str | None
    decidido_por: str | None
    dt_decisao: datetime | None


class DecisaoPropostasIn(BaseModel):
    ids: list[int] = Field(min_length=1)
    usuario: str = Field(min_length=3, max_length=60)


class ViaturaIn(BaseModel):
    placa: str = Field(min_length=7, max_length=8)
    modelo: str = Field(min_length=1, max_length=60)
    id_opm: int | None = None
    usuario: str = "demo.logistica"


class SituacaoCargaOut(BaseModel):
    aguardando_carga: int


class CargaIn(BaseModel):
    usuario: str = Field(min_length=3, max_length=60)


class LotadaOut(BaseModel):
    placa: str
    cd_unidade_legado: str
    ds_unidade_legado: str
    nome_opm: str


class ViaturaSemOpmOut(BaseModel):
    id_viatura: int
    placa: str
    modelo: str
    status_operacional: str
    cd_unidade_legado: str | None
    ds_unidade_legado: str | None
    motivo: str | None
    id_opm_sugerida: int | None
    nome_opm_sugerida: str | None


class InconformidadeOut(BaseModel):
    placa: str
    cd_unidade_legado: str | None
    ds_unidade_legado: str | None
    motivo: str
    opm_sugerida: str | None
    acao: str


class ResultadoCargaOut(BaseModel):
    simulacao: bool
    atualizadas: int
    contingencia: int
    de_para_criados: int
    propostas_criadas: int
    lotadas: list[LotadaOut]
    inconformidades: list[InconformidadeOut]
    relatorio: str | None
