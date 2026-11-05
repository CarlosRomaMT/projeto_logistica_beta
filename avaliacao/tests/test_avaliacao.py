"""Proteção de dados (item 07) e métricas do comparativo. Não acessam banco nem Ollama."""

import pytest

from avaliacao import conexao, diagnostico_real, gerar_gabarito
from avaliacao.conexao import ConsultaProibida, checar_sql
from avaliacao.metricas import HIBRIDO, QWEN, REGRA, calcular


@pytest.mark.parametrize("sql", [
    "SELECT placa FROM transporte.tb_veiculo",
    "SELECT cod_veiculo, chassi FROM transporte.tb_veiculo",
    "SELECT renavam FROM transporte.tb_veiculo",
    "SELECT obs FROM transporte.tb_veiculo",
    "SELECT log_inc_login FROM sgpm.opm",
    "SELECT telefone_1 FROM sgpm.opm",
    "SELECT * FROM transporte.tb_veiculo",
    "SELECT v.* FROM transporte.tb_veiculo v",
])
def test_consultas_com_dado_protegido_sao_bloqueadas(sql):
    with pytest.raises(ConsultaProibida):
        checar_sql(sql)


def test_contagens_e_colunas_de_codigo_sao_permitidas():
    checar_sql("SELECT count(*), cod_bairro FROM sgpm.opm")


@pytest.mark.parametrize("modulo", [diagnostico_real, gerar_gabarito])
def test_todas_as_consultas_do_projeto_passam_na_protecao(modulo):
    for sql in modulo.CONSULTAS.values():
        checar_sql(sql)


def test_url_vem_do_env_file_sem_o_driver_do_sqlalchemy(tmp_path, monkeypatch):
    monkeypatch.delenv("DIAG_DATABASE_URL", raising=False)
    arquivo = tmp_path / ".env"
    arquivo.write_text("OUTRA=1\nDATABASE_URL=postgresql+psycopg2://u:s@h:5432/b\n", encoding="utf-8")
    assert conexao.carregar_url(str(arquivo)) == "postgresql://u:s@h:5432/b"


def test_variavel_de_ambiente_tem_prioridade(tmp_path, monkeypatch):
    monkeypatch.setenv("DIAG_DATABASE_URL", "postgresql://env/b")
    assert conexao.carregar_url(None) == "postgresql://env/b"


def test_sem_configuracao_explica_o_que_falta(monkeypatch):
    monkeypatch.delenv("DIAG_DATABASE_URL", raising=False)
    with pytest.raises(conexao.ErroConexao, match="DIAG_DATABASE_URL"):
        conexao.carregar_url(None)


def linha(gabarito, regra_situacao, regra_id, ia_resultado="ACEITA", ia_id=None, no_top=True):
    return {"gabarito": gabarito, "regra_situacao": regra_situacao, "regra_id": regra_id,
            "ia_resultado": ia_resultado, "ia_id": ia_id, "ia_motivo": None if ia_resultado == "ACEITA" else "X",
            "ia_latencia_ms": 100, "gabarito_nas_candidatas": no_top}


def test_metricas_do_comparativo():
    linhas = [
        linha(1, "CONFIRMADO", 1, ia_id=1),                         # todos acertam
        linha(2, "CONFIRMADO", 9, ia_id=2),                         # confirmação automática errada
        linha(3, "SEM_CORRESPONDENCIA", None, ia_id=3),             # só a IA acerta
        linha(4, "PENDENTE", 4, ia_resultado="DESCARTADA"),         # IA descartada: híbrido usa a regra
        linha(5, "SEM_CORRESPONDENCIA", None, ia_resultado="INDISPONIVEL", no_top=False),
    ]
    m = calcular(linhas)
    assert (m[REGRA]["acertos"], m[REGRA]["erros"], m[REGRA]["sem_sugestao"]) == (2, 1, 2)
    assert m[REGRA]["confirmacoes_automaticas_erradas"] == 1
    assert (m[QWEN]["acertos"], m[QWEN]["sem_sugestao"]) == (3, 2)
    assert (m[HIBRIDO]["acertos"], m[HIBRIDO]["erros"]) == (3, 1)  # exata errada prevalece (sem IA)
    assert m[HIBRIDO]["origem"] == {"regra_exata": 2, "qwen": 1, "regra_similaridade": 1, "sem_sugestao": 1}
    assert m["ganho_do_hibrido"]["resolvidos_pelo_hibrido"] == 1
    assert m[QWEN]["gabarito_nas_candidatas"] == 0.8


def test_metricas_do_alerta_de_coerencia():
    linhas = [dict(linha(1, "SEM_CORRESPONDENCIA", None, ia_id=1), ia_alerta=False),
              dict(linha(2, "SEM_CORRESPONDENCIA", None, ia_id=9), ia_alerta=True),   # pegou um erro
              dict(linha(3, "SEM_CORRESPONDENCIA", None, ia_id=3), ia_alerta=True)]   # acerto com alerta
    m = calcular(linhas)
    assert (m[QWEN]["alertas_em_erros"], m[QWEN]["alertas_em_acertos"]) == (1, 1)


def test_metricas_sem_ia():
    m = calcular([linha(1, "CONFIRMADO", 1)], ia_executada=False)
    assert QWEN not in m and m[REGRA]["acuracia"] == 1.0
