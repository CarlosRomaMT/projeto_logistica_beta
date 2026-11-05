"""RF04 e RNF01: carga do legado para a coluna nova, via de-para confirmado."""

import csv

import pytest

from app.core.db import engine
from app.services import carga
from app.services import de_para as servico_de_para
from app.services.carga import executar_migracao

SQL_ATIVAS_SEM_OPM = """
    SELECT count(*) AS n FROM tb_viatura
    WHERE status_operacional <> 'BAIXADA' AND fk_id_opm_unidade IS NULL
"""


def ler_csv(caminho):
    with caminho.open(encoding="utf-8-sig") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def test_dry_run_nao_altera_o_banco(consultar, tmp_path):
    resultado = executar_migracao(dry_run=True, saida=tmp_path)

    assert resultado.atualizadas == 16
    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 16
    assert consultar("SELECT count(*) AS n FROM tb_de_para_unidade")[0]["n"] == 0
    assert list(tmp_path.iterdir()) == []


def test_carga_deixa_todas_as_ativas_com_opm(consultar, viatura, tmp_path):
    resultado = executar_migracao(saida=tmp_path)

    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 0
    assert viatura("ABC1A23")["fk_id_opm_unidade"] == 1   # '1º BPM - CENTRO'
    assert viatura("ABC2B34")["fk_id_opm_unidade"] == 1   # 'PRIMEIRO BATALHAO PM CENTRO'
    assert viatura("BCD1D11")["fk_id_opm_unidade"] == 2   # '2 B.P.M. NORTE'
    assert viatura("DEF1H11")["fk_id_opm_unidade"] == 4   # '1ª CIA IND PM'
    assert viatura("CDE1F11")["fk_id_opm_unidade"] == 0   # só parecida: aguarda validação
    assert viatura("HIJ1Q11")["fk_id_opm_unidade"] is None  # baixada fica de fora
    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 1     # já preenchida: não sobrescreve
    assert viatura("ABC1A23")["cd_unidade_legado"] == "101"
    assert viatura("BCD2E22")["fk_id_opm_unidade"] == 2     # cautelada: na implantação também é lotada
    assert resultado.contingencia == 9


def test_relatorio_lista_inconformidades_por_motivo(tmp_path):
    resultado = executar_migracao(saida=tmp_path)

    linhas = ler_csv(resultado.relatorio)
    motivos = {}
    for linha in linhas:
        motivos.setdefault(linha["motivo"], []).append(linha["placa"])
    assert motivos == {
        "DE_PARA_PENDENTE_VALIDACAO": ["CDE1F11", "CDE2G22"],
        "OPM_INATIVA": ["EFG1J11"],
        "LEGADO_NULO": ["FGH1K11", "FGH2L22", "FGH3M33"],
        "UNIDADE_LEGADO_INEXISTENTE": ["GHI1N11", "GHI3P33"],
        "SEM_CORRESPONDENCIA": ["GHI2O22"],
        "DIVERGENCIA_LEGADO_X_NOVO": ["JKL1S11"],
    }
    pendente = next(l for l in linhas if l["placa"] == "CDE1F11")
    assert pendente["opm_sugerida"] == "3º Batalhão de Polícia Militar - Sul"
    assert pendente["ds_unidade_legado"] == "3º BTL PM"


def test_segunda_execucao_nao_altera_nada(tmp_path):
    executar_migracao(saida=tmp_path)

    segunda = executar_migracao(saida=tmp_path)

    assert segunda.atualizadas == 0
    assert segunda.de_para_criados == 0


def test_de_para_confirmado_depois_tira_viaturas_da_contingencia(viatura, tmp_path):
    executar_migracao(saida=tmp_path)
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            UPDATE tb_de_para_unidade SET situacao = 'CONFIRMADO', metodo = 'MANUAL', fk_id_opm = 6
            WHERE cd_unidade_legado = '106'
        """)

    segunda = executar_migracao(saida=tmp_path)

    assert segunda.atualizadas == 1
    assert viatura("GHI2O22")["fk_id_opm_unidade"] == 6
    assert viatura("CDE1F11")["fk_id_opm_unidade"] == 0


def test_falha_no_meio_da_carga_desfaz_tudo(consultar, monkeypatch, tmp_path):
    original = servico_de_para.atualizar_viatura_da_contingencia
    chamadas = []

    def falhar_na_quinta(conn, id_viatura, id_opm):
        chamadas.append(id_viatura)
        if len(chamadas) == 5:
            raise RuntimeError("falha simulada")
        return original(conn, id_viatura, id_opm)

    monkeypatch.setattr(servico_de_para, "atualizar_viatura_da_contingencia", falhar_na_quinta)

    with pytest.raises(RuntimeError):
        executar_migracao(saida=tmp_path)

    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 16
    assert consultar("SELECT count(*) AS n FROM tb_de_para_unidade")[0]["n"] == 0
    assert list(tmp_path.iterdir()) == []


def test_carga_cria_proposta_de_correcao_para_divergencia(consultar, tmp_path):
    resultado = executar_migracao(saida=tmp_path)

    assert resultado.propostas_criadas == 1
    proposta = consultar("""
        SELECT v.placa, c.id_opm_atual, c.id_opm_proposta, c.situacao
        FROM tb_correcao_divergencia c JOIN tb_viatura v USING (id_viatura)
    """)
    assert [tuple(p.values()) for p in proposta] == [("JKL1S11", 1, 2, "PROPOSTA")]


def test_dry_run_nao_cria_propostas(consultar, tmp_path):
    assert executar_migracao(dry_run=True, saida=tmp_path).propostas_criadas == 1
    assert consultar("SELECT count(*) AS n FROM tb_correcao_divergencia")[0]["n"] == 0


def test_viatura_movimentada_pelo_sistema_novo_nao_e_divergencia(client, viatura, tmp_path):
    """Depois da implantação o legado fica congelado: movimentação legítima não pode virar divergência."""
    executar_migracao(saida=tmp_path)
    client.post(f"/api/viaturas/{viatura('ABC1A23')['id_viatura']}/movimentar", json={"id_opm_destino": 2})

    resultado = executar_migracao(saida=tmp_path)

    divergentes = [i["placa"] for i in resultado.inconformidades if i["motivo"] == "DIVERGENCIA_LEGADO_X_NOVO"]
    assert divergentes == ["JKL1S11"]


# --- Carga pela tela (painel "Carga da lotação") ---


@pytest.fixture
def relatorios(monkeypatch, tmp_path):
    monkeypatch.setattr(carga, "DIR_RELATORIOS", tmp_path)
    return tmp_path


def test_situacao_mostra_viaturas_aguardando_a_carga(client, relatorios):
    assert client.get("/api/carga").json() == {"aguardando_carga": 16}
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})
    assert client.get("/api/carga").json() == {"aguardando_carga": 0}


def test_simular_pela_tela_nao_grava_nada(client, consultar, relatorios):
    corpo = client.post("/api/carga/simular").json()

    assert (corpo["simulacao"], corpo["atualizadas"], corpo["contingencia"], corpo["relatorio"]) == (True, 16, 9, None)
    assert [(l["placa"], l["nome_opm"]) for l in corpo["lotadas"]][:2] == [
        ("ABC1A23", "1º Batalhão de Polícia Militar - Centro"), ("ABC2B34", "1º Batalhão de Polícia Militar - Centro"),
    ]
    assert len(corpo["lotadas"]) == 7  # 16 alteradas = 7 lotadas na OPM certa + 9 para a OPM 0
    assert len(corpo["inconformidades"]) == 10
    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 16
    assert list(relatorios.iterdir()) == []


def test_executar_pela_tela_grava_e_registra_quem_executou(client, consultar, relatorios):
    corpo = client.post("/api/carga/executar", json={"usuario": "sgt.revisor"}).json()

    assert (corpo["simulacao"], corpo["atualizadas"], corpo["propostas_criadas"]) == (False, 16, 1)
    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 0
    resp = client.get(f"/api/carga/relatorios/{corpo['relatorio']}")
    assert resp.status_code == 200
    linhas = list(csv.DictReader(resp.content.decode("utf-8-sig").splitlines(), delimiter=";"))
    assert len(linhas) == 10
    assert {l["executado_por"] for l in linhas} == {"sgt.revisor"}


def test_executar_pela_tela_exige_revisor(client, consultar, relatorios):
    assert client.post("/api/carga/executar", json={}).status_code == 422
    assert consultar(SQL_ATIVAS_SEM_OPM)[0]["n"] == 16


@pytest.mark.parametrize("nome", ["inconformidades_20260101_000000.csv", "02_seed.sql"])
def test_so_baixa_relatorio_de_inconformidades_existente(client, relatorios, nome):
    (relatorios / "02_seed.sql").write_text("segredo")
    assert client.get(f"/api/carga/relatorios/{nome}").status_code == 404


# --- Etapa 4: viaturas que ficaram na OPM 0 ---


def test_sem_opm_lista_o_que_a_carga_nao_resolveu_com_motivo(client, relatorios):
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})

    linhas = {v["placa"]: v for v in client.get("/api/carga/sem-opm").json()}

    assert sorted(linhas) == ["CDE1F11", "CDE2G22", "EFG1J11", "FGH1K11", "FGH2L22",
                              "FGH3M33", "GHI1N11", "GHI2O22", "GHI3P33"]
    assert (linhas["CDE1F11"]["motivo"], linhas["CDE1F11"]["id_opm_sugerida"]) == ("DE_PARA_PENDENTE_VALIDACAO", 3)
    assert (linhas["EFG1J11"]["motivo"], linhas["EFG1J11"]["id_opm_sugerida"]) == ("OPM_INATIVA", None)
    assert linhas["GHI3P33"]["motivo"] == "UNIDADE_LEGADO_INEXISTENTE"


def test_lotar_pela_etapa_4_tira_a_viatura_da_lista(client, viatura, relatorios):
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})

    resp = client.post(f"/api/carga/sem-opm/{viatura('FGH1K11')['id_viatura']}/lotar",
                       json={"id_opm": 1, "usuario": "sgt.revisor"})

    assert resp.status_code == 200
    assert "FGH1K11" not in {v["placa"] for v in client.get("/api/carga/sem-opm").json()}


def test_etapa_4_lota_viatura_cautelada_mas_a_operacao_continua_bloqueando(client, viatura, consultar, relatorios):
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})
    id_cautelada = viatura("GHI3P33")["id_viatura"]

    pela_operacao = client.post(f"/api/viaturas/{id_cautelada}/movimentar", json={"id_opm_destino": 1})
    pela_implantacao = client.post(f"/api/carga/sem-opm/{id_cautelada}/lotar",
                                   json={"id_opm": 1, "usuario": "sgt.revisor"})

    assert pela_operacao.status_code == 409
    assert pela_implantacao.status_code == 200
    assert viatura("GHI3P33")["fk_id_opm_unidade"] == 1
    historico = consultar("""
        SELECT h.tipo, h.usuario FROM tb_historico_movimentacao h
        JOIN tb_viatura v USING (id_viatura) WHERE v.placa = 'GHI3P33'
    """)
    assert [tuple(h.values()) for h in historico] == [("LOTACAO_IMPLANTACAO", "sgt.revisor")]


def test_etapa_4_so_lota_viatura_que_esta_na_opm_0(client, viatura, relatorios):
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})

    resp = client.post(f"/api/carga/sem-opm/{viatura('ABC1A23')['id_viatura']}/lotar",
                       json={"id_opm": 2, "usuario": "sgt.revisor"})

    assert resp.status_code == 409
    assert viatura("ABC1A23")["fk_id_opm_unidade"] == 1


def test_etapa_4_recusa_opm_inativa_e_baixada(client, viatura, consultar, relatorios):
    client.post("/api/carga/executar", json={"usuario": "sgt.revisor"})
    id_fgh = viatura("FGH1K11")["id_viatura"]

    assert client.post(f"/api/carga/sem-opm/{id_fgh}/lotar", json={"id_opm": 5, "usuario": "sgt.revisor"}).status_code == 422
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE tb_viatura SET status_operacional = 'BAIXADA' WHERE placa = 'FGH1K11'")
    assert client.post(f"/api/carga/sem-opm/{id_fgh}/lotar", json={"id_opm": 1, "usuario": "sgt.revisor"}).status_code == 409
    assert viatura("FGH1K11")["fk_id_opm_unidade"] == 0
