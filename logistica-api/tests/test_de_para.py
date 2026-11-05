"""Comparação de descrições e fluxo de validação humana do de-para."""

import csv

import pytest
from fastapi.testclient import TestClient

from app import main
from app.core.db import engine
from app.errors import MSG_OPM_INVALIDA
from app.main import app
from app.services.carga import executar_migracao
from app.services.de_para import normalizar, similaridade, sincronizar_de_para, sugerir_opm
from scripts.de_para import exportar_para_revisao, importar_revisao

OPMS = [
    {"id_opm": 1, "nome": "1º Batalhão de Polícia Militar - Centro"},
    {"id_opm": 2, "nome": "2º Batalhão de Polícia Militar - Norte"},
    {"id_opm": 3, "nome": "3º Batalhão de Polícia Militar - Sul"},
    {"id_opm": 4, "nome": "1ª Companhia Independente de Polícia Militar"},
    {"id_opm": 6, "nome": "Batalhão de Polícia Militar de Trânsito"},
]


@pytest.mark.parametrize("descricao", [
    "1º BPM - CENTRO", "1 B.P.M. Centro", "PRIMEIRO BATALHAO PM CENTRO", "1o btl pm centro",
])
def test_grafias_diferentes_da_mesma_unidade_normalizam_igual(descricao):
    assert normalizar(descricao) == normalizar("1º Batalhão de Polícia Militar - Centro")


def test_numero_diferente_nunca_corresponde():
    assert similaridade(normalizar("1º BPM - Centro"), normalizar("2º BPM - Centro")) == 0.0


def test_igualdade_exata_confirma_automaticamente():
    sugestao = sugerir_opm("1ª CIA IND PM", OPMS)

    assert (sugestao.situacao, sugestao.id_opm, sugestao.metodo) == ("CONFIRMADO", 4, "EXATO")


def test_semelhanca_vira_sugestao_pendente():
    sugestao = sugerir_opm("3º BTL PM", OPMS)

    assert (sugestao.situacao, sugestao.id_opm, sugestao.metodo) == ("PENDENTE", 3, "SIMILARIDADE")
    assert 0.75 <= sugestao.score < 1


def test_sigla_desconhecida_fica_sem_correspondencia():
    sugestao = sugerir_opm("BPTRAN", OPMS)

    assert (sugestao.situacao, sugestao.id_opm) == ("SEM_CORRESPONDENCIA", None)


def test_nomes_duplicados_nao_sao_confirmados_automaticamente():
    duplicadas = OPMS + [{"id_opm": 9, "nome": "1ª Cia. Independente de PM"}]

    assert sugerir_opm("1ª CIA IND PM", duplicadas).situacao == "PENDENTE"


def test_sincronizacao_nao_sobrescreve_decisao_humana(consultar):
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            INSERT INTO tb_de_para_unidade (cd_unidade_legado, ds_unidade_legado, fk_id_opm, situacao, metodo)
            VALUES ('106', 'BPTRAN', 6, 'CONFIRMADO', 'MANUAL')
        """)
        criadas = sincronizar_de_para(conn)

    assert criadas == 9  # 10 unidades antigas, uma já decidida
    manual = consultar("SELECT * FROM tb_de_para_unidade WHERE cd_unidade_legado = '106'")[0]
    assert (manual["fk_id_opm"], manual["metodo"]) == (6, "MANUAL")


def test_sincronizacao_repetida_nao_cria_nada():
    with engine.begin() as conn:
        assert sincronizar_de_para(conn) == 10
        assert sincronizar_de_para(conn) == 0


def test_subida_da_api_deixa_o_de_para_pronto_para_revisao(consultar):
    lotacao = "SELECT placa, fk_id_opm_unidade FROM tb_viatura ORDER BY placa"
    antes = consultar(lotacao)
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            INSERT INTO tb_de_para_unidade (cd_unidade_legado, ds_unidade_legado, fk_id_opm, situacao, metodo)
            VALUES ('106', 'BPTRAN', 6, 'CONFIRMADO', 'MANUAL')
        """)

    with TestClient(app) as client:  # o `with` dispara o lifespan
        de_para = client.get("/api/de-para").json()

    assert len(de_para) == 10
    assert {d["cd_unidade_legado"]: d["situacao"] for d in de_para}["103"] == "PENDENTE"
    manual = consultar("SELECT fk_id_opm, metodo FROM tb_de_para_unidade WHERE cd_unidade_legado = '106'")[0]
    assert (manual["fk_id_opm"], manual["metodo"]) == (6, "MANUAL")
    assert consultar(lotacao) == antes


def test_falha_no_de_para_nao_impede_a_api_de_subir(monkeypatch, consultar):
    def falhar(_conn):
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(main, "sincronizar_de_para", falhar)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
    assert consultar("SELECT count(*) AS n FROM tb_de_para_unidade")[0]["n"] == 0


def preencher_revisao(caminho, confirmacoes):
    with caminho.open(encoding="utf-8-sig") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    for linha in linhas:
        linha["id_opm_confirmada"] = confirmacoes.get(linha["cd_unidade_legado"], "")
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=linhas[0].keys(), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def test_revisao_exportada_e_importada_confirma_o_de_para(consultar, tmp_path):
    with engine.begin() as conn:
        sincronizar_de_para(conn)
        caminho = exportar_para_revisao(conn, tmp_path)
    preencher_revisao(caminho, {"103": "3", "106": "6"})

    assert importar_revisao(caminho, "sgt.revisor").confirmadas == 2

    linhas = consultar("""
        SELECT cd_unidade_legado, fk_id_opm, situacao, metodo FROM tb_de_para_unidade
        WHERE cd_unidade_legado IN ('103', '106') ORDER BY 1
    """)
    assert [tuple(l.values()) for l in linhas] == [
        ("103", 3, "CONFIRMADO", "MANUAL"), ("106", 6, "CONFIRMADO", "MANUAL"),
    ]


def test_importacao_aceita_csv_salvo_pelo_excel_com_virgula_e_sem_bom(consultar, tmp_path):
    with engine.begin() as conn:
        sincronizar_de_para(conn)
    caminho = tmp_path / "revisado.csv"
    caminho.write_text(
        "cd_unidade_legado,ds_unidade_legado,score,id_opm_confirmada\r\n"
        "103,3º BTL PM,929,3\r\n106,BPTRAN,308,\r\n",
        encoding="utf-8",
    )

    assert importar_revisao(caminho, "sgt.revisor").confirmadas == 1
    assert consultar("SELECT situacao FROM tb_de_para_unidade WHERE cd_unidade_legado = '103'")[0]["situacao"] == "CONFIRMADO"


def test_importacao_sem_a_coluna_de_confirmacao_explica_o_erro(tmp_path):
    caminho = tmp_path / "errado.csv"
    caminho.write_text("cd_unidade_legado;ds_unidade_legado\n103;3º BTL PM\n", encoding="utf-8")

    with pytest.raises(ValueError, match="id_opm_confirmada"):
        importar_revisao(caminho, "sgt.revisor")


def test_importacao_com_opm_invalida_nao_grava_nada(consultar, tmp_path):
    with engine.begin() as conn:
        sincronizar_de_para(conn)
        caminho = exportar_para_revisao(conn, tmp_path)
    preencher_revisao(caminho, {"103": "3", "106": "999"})

    with pytest.raises(ValueError, match="OPM 999"):
        importar_revisao(caminho, "sgt.revisor")

    situacao = consultar("SELECT situacao FROM tb_de_para_unidade WHERE cd_unidade_legado = '103'")
    assert situacao[0]["situacao"] == "PENDENTE"


def test_importacao_com_opm_inativa_nao_grava_nada(consultar, tmp_path):
    with engine.begin() as conn:
        sincronizar_de_para(conn)
        caminho = exportar_para_revisao(conn, tmp_path)
    preencher_revisao(caminho, {"106": "5"})

    with pytest.raises(ValueError, match="OPM 5"):
        importar_revisao(caminho, "sgt.revisor")

    assert consultar("SELECT situacao FROM tb_de_para_unidade WHERE cd_unidade_legado = '106'")[0]["situacao"] == "SEM_CORRESPONDENCIA"


# --- Tela de validação (Melhoria 2) ---


@pytest.fixture
def apos_carga(tmp_path):
    executar_migracao(saida=tmp_path)


def test_importacao_tira_viaturas_da_contingencia_sem_nova_carga(viatura, consultar, apos_carga, tmp_path):
    with engine.begin() as conn:
        caminho = exportar_para_revisao(conn, tmp_path)
    preencher_revisao(caminho, {"103": "3", "106": "6"})

    resultado = importar_revisao(caminho, "sgt.revisor")

    assert (resultado.movidas, resultado.bloqueadas) == (["CDE1F11", "CDE2G22", "GHI2O22"], [])
    assert viatura("CDE1F11")["fk_id_opm_unidade"] == 3
    assert viatura("GHI2O22")["fk_id_opm_unidade"] == 6
    historico = consultar("SELECT tipo, usuario FROM tb_historico_movimentacao")
    assert [tuple(h.values()) for h in historico] == [("CORRECAO_DE_PARA", "sgt.revisor")] * 3


def test_listagem_traz_pendentes_primeiro_com_viaturas_na_contingencia(client, apos_carga):
    de_para = client.get("/api/de-para").json()

    assert [(d["cd_unidade_legado"], d["situacao"], d["qtd_viaturas_contingencia"]) for d in de_para[:3]] == [
        ("103", "PENDENTE", 2), ("106", "SEM_CORRESPONDENCIA", 1), ("107", "SEM_CORRESPONDENCIA", 1),
    ]
    assert de_para[0]["nome_opm"] == "2ª CIA PM - 1º BPM"


def test_confirmar_na_tela_tira_viaturas_da_contingencia_com_historico(client, viatura, consultar, apos_carga):
    resp = client.post("/api/de-para/103/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["movidas"] == ["CDE1F11", "CDE2G22"]
    assert corpo["bloqueadas"] == []
    assert (corpo["de_para"]["situacao"], corpo["de_para"]["confirmado_por"]) == ("CONFIRMADO", "sgt.revisor")
    assert corpo["de_para"]["qtd_viaturas_contingencia"] == 0
    assert viatura("CDE1F11")["fk_id_opm_unidade"] == 3
    assert viatura("CDE1F11")["cd_unidade_legado"] == "103"
    historico = consultar("SELECT tipo, id_opm_origem, id_opm_destino, usuario FROM tb_historico_movimentacao")
    assert {tuple(h.values()) for h in historico} == {("CORRECAO_DE_PARA", 0, 3, "sgt.revisor")}


def test_confirmar_lota_tambem_viatura_cautelada(client, viatura, consultar, apos_carga):
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE tb_viatura SET status_operacional = 'CAUTELADA' WHERE placa = 'CDE2G22'")

    corpo = client.post("/api/de-para/103/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"}).json()

    # Na implantação a cautela não impede a lotação (decisão da gestão de frota).
    assert corpo["movidas"] == ["CDE1F11", "CDE2G22"]
    assert corpo["bloqueadas"] == []
    assert viatura("CDE2G22")["fk_id_opm_unidade"] == 3


@pytest.mark.parametrize("id_opm", [5, 0, 999, None])
def test_confirmar_com_opm_invalida_nao_grava_nada(client, viatura, consultar, apos_carga, id_opm):
    resp = client.post("/api/de-para/103/confirmar", json={"id_opm": id_opm, "usuario": "sgt.revisor"})

    assert resp.status_code == 422
    assert resp.json()["detail"] == MSG_OPM_INVALIDA
    assert consultar("SELECT situacao FROM tb_de_para_unidade WHERE cd_unidade_legado = '103'")[0]["situacao"] == "PENDENTE"
    assert viatura("CDE1F11")["fk_id_opm_unidade"] == 0


def test_confirmar_unidade_inexistente_ou_sem_revisor(client, apos_carga):
    assert client.post("/api/de-para/777/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"}).status_code == 404
    assert client.post("/api/de-para/103/confirmar", json={"id_opm": 3}).status_code == 422


# --- Alterar uma associação já confirmada ---


@pytest.fixture
def unidade_de_opm_extinta(tmp_path):
    """Caso raro no banco real (fora do seed): unidade antiga cujo nome é idêntico ao de uma OPM extinta."""
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO tb_unidade_legado (cd_unidade, ds_unidade)"
                             " VALUES ('150', '5º BPM - BOA VISTA DO SUL')")
        conn.exec_driver_sql("INSERT INTO tb_viatura (placa, modelo, status_operacional, cd_unidade_legado)"
                             " VALUES ('EXT1A11', 'Renault Duster', 'DISPONIVEL', '150')")
    executar_migracao(saida=tmp_path)


def test_associacao_a_opm_inativa_aparece_entre_as_pendentes(client, viatura, unidade_de_opm_extinta):
    de_para = client.get("/api/de-para").json()

    inativa = next(d for d in de_para if d["cd_unidade_legado"] == "150")
    assert (inativa["situacao"], inativa["status_opm"]) == ("CONFIRMADO", "INATIVA")
    assert inativa in de_para[:7]  # junto das que precisam de decisão, antes das resolvidas
    assert viatura("EXT1A11")["fk_id_opm_unidade"] == 0  # a carga não usa OPM inativa


def test_reassociar_unidade_de_opm_inativa_tira_a_viatura_da_opm_0(client, viatura, unidade_de_opm_extinta):
    corpo = client.post("/api/de-para/150/confirmar", json={"id_opm": 1, "usuario": "sgt.revisor"}).json()

    assert corpo["movidas"] == ["EXT1A11"]
    assert viatura("EXT1A11")["fk_id_opm_unidade"] == 1


def test_alterar_associacao_corrige_viaturas_lotadas_pela_carga(client, viatura, consultar, apos_carga):
    # ABC1A23 já foi movimentada pelo sistema novo: a lotação dela é uma decisão, não vem da associação.
    client.post(f"/api/viaturas/{viatura('ABC1A23')['id_viatura']}/movimentar", json={"id_opm_destino": 4})

    corpo = client.post("/api/de-para/101/confirmar", json={"id_opm": 2, "usuario": "sgt.revisor"}).json()

    assert corpo["movidas"] == ["ABC3C45"]
    assert viatura("ABC3C45")["fk_id_opm_unidade"] == 2
    assert viatura("ABC1A23")["fk_id_opm_unidade"] == 4
    historico = consultar("""
        SELECT h.tipo, h.id_opm_origem, h.id_opm_destino FROM tb_historico_movimentacao h
        JOIN tb_viatura v USING (id_viatura) WHERE v.placa = 'ABC3C45'
    """)
    assert [tuple(h.values()) for h in historico] == [("CORRECAO_DE_PARA", 1, 2)]

