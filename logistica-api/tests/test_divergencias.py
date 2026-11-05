"""Melhoria 1: correção das divergências (coluna nova x legado) com decisão humana."""

import pytest
from sqlalchemy import text

from app.core.db import engine
from app.services.carga import executar_migracao


@pytest.fixture(autouse=True)
def apos_carga(tmp_path):
    executar_migracao(saida=tmp_path)  # cria a proposta da JKL1S11 (coluna nova 1, legado -> 2)


@pytest.fixture
def executar():
    def _executar(sql: str, **params):
        with engine.begin() as conn:
            conn.execute(text(sql), params)
    return _executar


def propostas(client, situacao="PROPOSTA"):
    return {p["placa"]: p for p in client.get("/api/divergencias").json() if p["situacao"] == situacao}


def test_lista_proposta_com_opm_atual_e_proposta(client):
    jkl = propostas(client)["JKL1S11"]

    assert (jkl["nome_opm_atual"], jkl["nome_opm_proposta"]) == (
        "1º Batalhão de Polícia Militar - Centro", "2º Batalhão de Polícia Militar - Norte")
    assert (jkl["cd_unidade_legado"], jkl["ds_unidade_legado"]) == ("102", "2 B.P.M. NORTE")
    assert jkl["bloqueio"] is None


def test_aplicar_move_pelo_servico_e_registra_decisao(client, viatura, consultar):
    id_proposta = propostas(client)["JKL1S11"]["id"]

    resp = client.post("/api/divergencias/aplicar", json={"ids": [id_proposta], "usuario": "cap.gestor"})

    assert resp.json() == {"aplicadas": ["JKL1S11"]}
    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 2
    assert viatura("JKL1S11")["cd_unidade_legado"] == "102"
    historico = consultar("SELECT tipo, id_opm_origem, id_opm_destino, usuario FROM tb_historico_movimentacao")
    assert [tuple(h.values()) for h in historico] == [("CORRECAO_CARGA", 1, 2, "cap.gestor")]
    aplicada = propostas(client, "APLICADA")["JKL1S11"]
    assert aplicada["decidido_por"] == "cap.gestor"
    # Corrigida, tem histórico: não volta a ser proposta.
    assert client.post("/api/divergencias/procurar").json() == {"criadas": 0}


def test_rejeitada_nao_volta_a_ser_proposta(client, viatura):
    id_proposta = propostas(client)["JKL1S11"]["id"]

    client.post("/api/divergencias/rejeitar", json={"ids": [id_proposta], "usuario": "cap.gestor"})

    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 1
    assert propostas(client) == {}
    assert client.post("/api/divergencias/procurar").json() == {"criadas": 0}


def test_viatura_cautelada_e_corrigida_na_implantacao(client, viatura, executar):
    executar("UPDATE tb_viatura SET status_operacional = 'CAUTELADA' WHERE placa = 'JKL1S11'")
    jkl = propostas(client)["JKL1S11"]

    resp = client.post("/api/divergencias/aplicar", json={"ids": [jkl["id"]], "usuario": "cap.gestor"})

    assert jkl["bloqueio"] is None
    assert resp.status_code == 200
    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 2


def test_viatura_baixada_continua_bloqueada(client, viatura, executar):
    executar("UPDATE tb_viatura SET status_operacional = 'BAIXADA' WHERE placa = 'JKL1S11'")
    jkl = propostas(client)["JKL1S11"]

    resp = client.post("/api/divergencias/aplicar", json={"ids": [jkl["id"]], "usuario": "cap.gestor"})

    assert jkl["bloqueio"] == "BAIXADA"
    assert resp.status_code == 409
    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 1


def test_lote_e_tudo_ou_nada(client, viatura, executar):
    # Simula outra viatura desatualizada pelo sistema antigo: legado 104 (OPM 4), coluna nova 1.
    executar("UPDATE tb_viatura SET fk_id_opm_unidade = 1 WHERE placa = 'DEF1H11'")
    assert client.post("/api/divergencias/procurar").json() == {"criadas": 1}
    executar("UPDATE tb_viatura SET status_operacional = 'BAIXADA' WHERE placa = 'JKL1S11'")
    abertas = propostas(client)

    resp = client.post("/api/divergencias/aplicar",
                       json={"ids": [abertas["DEF1H11"]["id"], abertas["JKL1S11"]["id"]], "usuario": "cap.gestor"})

    assert resp.status_code == 409
    assert viatura("DEF1H11")["fk_id_opm_unidade"] == 1
    assert set(propostas(client)) == {"DEF1H11", "JKL1S11"}


def test_viatura_que_mudou_depois_da_proposta_nao_e_corrigida(client, viatura):
    id_proposta = propostas(client)["JKL1S11"]["id"]
    client.post(f"/api/viaturas/{viatura('JKL1S11')['id_viatura']}/movimentar", json={"id_opm_destino": 3})

    resp = client.post("/api/divergencias/aplicar", json={"ids": [id_proposta], "usuario": "cap.gestor"})

    assert resp.status_code == 409
    assert "mudou de OPM" in resp.json()["detail"]
    assert viatura("JKL1S11")["fk_id_opm_unidade"] == 3


def test_decisao_exige_revisor_e_ids(client):
    id_proposta = propostas(client)["JKL1S11"]["id"]

    assert client.post("/api/divergencias/aplicar", json={"ids": [id_proposta]}).status_code == 422
    assert client.post("/api/divergencias/aplicar", json={"ids": [], "usuario": "cap.gestor"}).status_code == 422
    assert client.post("/api/divergencias/rejeitar", json={"ids": [9999], "usuario": "cap.gestor"}).status_code == 409
