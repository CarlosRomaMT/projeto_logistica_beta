"""Conexão SOMENTE LEITURA com o banco de desenvolvimento, com bloqueio de colunas protegidas.

A URL nunca fica no código nem é impressa: vem de DIAG_DATABASE_URL ou da chave DATABASE_URL
de um arquivo .env informado em --env-file.
"""

import os
import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# Colunas que nenhuma consulta desta pasta pode ler (identificação de veículo, valores,
# texto livre, contatos, localização, pessoas e trilhas de auditoria com login/IP).
COLUNAS_PROTEGIDAS = re.compile(
    r"\b(placa|chassi|renavam|valor|obs|prefixo|pref_in|pref_fim|vtr_substituida|endereco|n_endereco"
    r"|bairro|cep|telefone\w*|e_?mail|latitude|longitude|cod_comandante|cod_proprietario|log_\w+)\b",
    re.IGNORECASE,
)
SELECAO_TOTAL = re.compile(r"select\s+(distinct\s+)?\*|\w+\.\*", re.IGNORECASE)

# Vigência em sgpm.opm (validado com o negócio em 2026-11-05):
# S = vigente, N = não vigente; E e C são desconsiderados (tratados à parte, nunca como vigentes).
VIGENTE = "S"
NAO_VIGENTE = "N"

# Situações de transporte.tb_veiculo consideradas frota operacional:
# 1 ATIVO, 2 MANUTENÇÃO PREVENTIVA, 8 CARRO RESERVA.
SITUACOES_OPERACIONAIS = (1, 2, 8)


class ConsultaProibida(Exception):
    pass


class ErroConexao(Exception):
    pass


def checar_sql(sql: str) -> None:
    if (achado := COLUNAS_PROTEGIDAS.search(sql)) is not None:
        raise ConsultaProibida(f"Consulta bloqueada: a coluna protegida '{achado.group(0)}' não pode ser lida.")
    if SELECAO_TOTAL.search(sql):
        raise ConsultaProibida("Consulta bloqueada: liste as colunas (SELECT * pode trazer dado protegido).")


def carregar_url(env_file: str | None) -> str:
    url = os.environ.get("DIAG_DATABASE_URL")
    if not url and env_file:
        caminho = Path(env_file)
        if not caminho.is_file():
            raise ErroConexao(f"Arquivo de configuração não encontrado: {caminho}")
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == "DATABASE_URL":
                url = valor.strip().strip('"').strip("'")
                break
    if not url:
        raise ErroConexao("Informe a conexão em DIAG_DATABASE_URL ou com --env-file <arquivo .env com DATABASE_URL>.")
    # Remove o driver do SQLAlchemy (postgresql+psycopg2:// -> postgresql://).
    return re.sub(r"^postgres(ql)?\+\w+://", "postgresql://", url)


def conectar(url: str) -> psycopg.Connection:
    try:
        return psycopg.connect(
            url,
            autocommit=True,
            connect_timeout=15,
            application_name="diagnostico_lotacao_mvp",
            options="-c default_transaction_read_only=on -c statement_timeout=60000",
        )
    except psycopg.OperationalError as erro:
        # A mensagem do psycopg não traz a senha, mas a URL completa não é repetida aqui.
        primeira_linha = str(erro).strip().splitlines()[0] if str(erro).strip() else "erro desconhecido"
        raise ErroConexao(f"Não foi possível conectar ao banco de diagnóstico (VPN/credenciais?): {primeira_linha}") from None


def consultar(conn: psycopg.Connection, sql: str, params: dict | None = None) -> list[dict]:
    checar_sql(sql)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()
