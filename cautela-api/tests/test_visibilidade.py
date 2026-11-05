"""RF02: o P4 vê só as viaturas disponíveis da sua OPM, pela coluna nova."""


def placas(client, login):
    resp = client.get("/api/frota/disponivel", headers={"X-Usuario-P4": login})
    assert resp.status_code == 200
    return [v["placa"] for v in resp.json()["viaturas"]]


def test_p4_ve_apenas_a_propria_opm_pela_coluna_nova(client):
    # JKL1S11 tem legado '102' mas coluna nova = 1: vale a coluna nova.
    assert placas(client, "p4.opm1") == ["JKL1S11"]
    assert placas(client, "p4.opm3") == ["JKL2T22"]
    # Antes da carga, as viaturas só com legado ficam invisíveis (o problema original).
    assert placas(client, "p4.opm2") == []


def test_somente_status_disponivel_aparece(client, executar):
    executar("UPDATE tb_viatura SET fk_id_opm_unidade = 1 WHERE cd_unidade_legado IN ('101', '111')")

    # ABC3C45 (manutenção) e HIJ1Q11 (baixada) não aparecem.
    assert placas(client, "p4.opm1") == ["ABC1A23", "ABC2B34", "JKL1S11"]

    executar("UPDATE tb_viatura SET status_operacional = 'CAUTELADA' WHERE placa = 'ABC1A23'")
    assert placas(client, "p4.opm1") == ["ABC2B34", "JKL1S11"]


def test_movimentacao_reflete_na_proxima_leitura(client, executar):
    executar("UPDATE tb_viatura SET fk_id_opm_unidade = 2 WHERE placa = 'JKL1S11'")

    assert "JKL1S11" not in placas(client, "p4.opm1")
    assert placas(client, "p4.opm2") == ["JKL1S11"]


def test_contingencia_so_aparece_para_p4_da_opm_0(client, executar):
    executar("UPDATE tb_viatura SET fk_id_opm_unidade = 0 WHERE placa = 'GHI1N11'")

    assert placas(client, "p4.contingencia") == ["GHI1N11"]
    assert "GHI1N11" not in placas(client, "p4.opm1")


def test_p4_nao_identificado(client):
    assert client.get("/api/frota/disponivel").status_code == 401
    assert client.get("/api/frota/disponivel", headers={"X-Usuario-P4": "intruso"}).status_code == 401


def test_resposta_nao_e_cacheada(client):
    resp = client.get("/api/frota/disponivel", headers={"X-Usuario-P4": "p4.opm1"})
    assert resp.headers["Cache-Control"] == "no-store"
