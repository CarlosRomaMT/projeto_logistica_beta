"""RF01, RF03 e RNF01: serviço de movimentação."""

import pytest

from app.errors import MSG_OPM_INVALIDA
from app.services import movimentacao
from app.services.carga import executar_migracao


def contar(consultar, tabela):
    return consultar(f"SELECT count(*) AS n FROM {tabela}")[0]["n"]


def test_movimentacao_grava_somente_coluna_nova(client, viatura, consultar):
    antes = viatura("JKL2T22")

    resp = client.post(f"/api/viaturas/{antes['id_viatura']}/movimentar", json={"id_opm_destino": 2})

    assert resp.status_code == 200
    assert resp.json()["id_opm"] == 2
    depois = viatura("JKL2T22")
    assert depois["fk_id_opm_unidade"] == 2
    assert depois["cd_unidade_legado"] == antes["cd_unidade_legado"]  # legado intocado
    historico = consultar("SELECT * FROM tb_historico_movimentacao")
    assert [(h["id_opm_origem"], h["id_opm_destino"]) for h in historico] == [(3, 2)]
    assert contar(consultar, "tb_notificacao_pendente") == 1


def test_movimentacao_de_viatura_sem_lotacao(client, viatura):
    id_viatura = viatura("ABC1A23")["id_viatura"]

    resp = client.post(f"/api/viaturas/{id_viatura}/movimentar", json={"id_opm_destino": 1})

    assert resp.status_code == 200
    assert viatura("ABC1A23")["fk_id_opm_unidade"] == 1
    assert viatura("ABC1A23")["cd_unidade_legado"] == "101"


@pytest.mark.parametrize("corpo", [
    {},                          # unidade em branco
    {"id_opm_destino": None},
    {"id_opm_destino": 5},       # OPM extinta
    {"id_opm_destino": 999},     # OPM inexistente
    {"id_opm_destino": 0},       # contingência não é destino válido
])
def test_opm_invalida_bloqueia_com_mensagem_oficial(client, viatura, consultar, corpo):
    id_viatura = viatura("JKL2T22")["id_viatura"]

    resp = client.post(f"/api/viaturas/{id_viatura}/movimentar", json=corpo)

    assert resp.status_code == 422
    assert resp.json() == {"detail": MSG_OPM_INVALIDA}
    assert viatura("JKL2T22")["fk_id_opm_unidade"] == 3
    assert contar(consultar, "tb_historico_movimentacao") == 0


@pytest.mark.parametrize("placa", ["HIJ1Q11", "BCD2E22"])  # baixada, cautelada
def test_status_da_viatura_impede_movimentacao(client, viatura, placa):
    resp = client.post(f"/api/viaturas/{viatura(placa)['id_viatura']}/movimentar",
                       json={"id_opm_destino": 2})

    assert resp.status_code == 409
    assert viatura(placa)["fk_id_opm_unidade"] is None


def test_viatura_inexistente(client):
    assert client.post("/api/viaturas/99999/movimentar", json={"id_opm_destino": 2}).status_code == 404


def test_falha_na_notificacao_desfaz_tudo(client, viatura, consultar, monkeypatch):
    """RNF01: erro no último passo desfaz a lotação e o histórico já gravados."""
    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha simulada (ex.: timeout de rede)")
    monkeypatch.setattr(movimentacao, "_registrar_notificacao", falhar)
    id_viatura = viatura("JKL2T22")["id_viatura"]

    with pytest.raises(RuntimeError):
        movimentacao.mover_viatura(id_viatura, 2, "teste")

    assert viatura("JKL2T22")["fk_id_opm_unidade"] == 3
    assert contar(consultar, "tb_historico_movimentacao") == 0
    assert contar(consultar, "tb_notificacao_pendente") == 0


def test_criacao_grava_coluna_nova_e_nao_o_legado(client, viatura):
    resp = client.post("/api/viaturas", json={"placa": "zzz9z99", "modelo": "Toyota Hilux", "id_opm": 4})

    assert resp.status_code == 201
    nova = viatura("ZZZ9Z99")
    assert nova["fk_id_opm_unidade"] == 4
    assert nova["cd_unidade_legado"] is None


def test_criacao_com_opm_inativa_nao_grava(client, consultar):
    resp = client.post("/api/viaturas", json={"placa": "ZZZ9Z99", "modelo": "Hilux", "id_opm": 5})

    assert resp.status_code == 422
    assert resp.json()["detail"] == MSG_OPM_INVALIDA
    assert consultar("SELECT * FROM tb_viatura WHERE placa = 'ZZZ9Z99'") == []


def test_listagem_nao_expoe_coluna_legada(client):
    viaturas = client.get("/api/viaturas").json()

    assert len(viaturas) == 23
    assert all("cd_unidade_legado" not in v for v in viaturas)


def test_diagnostico_mostra_unidade_antiga_e_de_para(client, tmp_path):
    executar_migracao(saida=tmp_path)  # cria o de-para

    legado = {v["cd_unidade_legado"]: v for v in client.get("/api/diagnostico/legado").json()}

    assert legado["111"]["ds_unidade_legado"] == "PRIMEIRO BATALHAO PM SANTA AURORA"
    assert (legado["111"]["situacao_de_para"], legado["111"]["id_opm_de_para"]) == ("CONFIRMADO", 1)
    assert legado["103"]["situacao_de_para"] == "PENDENTE"
    assert legado["999"]["ds_unidade_legado"] is None


def test_busca_de_opms_oferece_so_ativas_e_sem_contingencia(client):
    ids = [o["id_opm"] for o in client.get("/api/opms").json()]

    assert 5 not in ids  # extinta
    assert 0 not in ids  # contingência


@pytest.mark.parametrize("termo, esperado", [
    ("trânsito", [6]),   # o cadastro grava sem acento (TRANSITO): a busca ignora acentos
    ("Rio Claro", [7]),  # ignora maiúsculas
    ("RPMON", [11]),     # também pela abreviatura
])
def test_busca_de_opms_ignora_acento_e_usa_abreviatura(client, termo, esperado):
    assert [o["id_opm"] for o in client.get("/api/opms", params={"q": termo}).json()] == esperado
