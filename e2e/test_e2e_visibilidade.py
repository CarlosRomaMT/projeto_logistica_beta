"""Ponta a ponta com o ambiente no ar: a Logística move, o P4 de destino vê (RNF02).

Uso (PowerShell): docker compose run --rm -v ${PWD}/e2e:/e2e logistica-api pytest /e2e -s
"""

import os
import time

import httpx

LOGISTICA = os.environ.get("LOGISTICA_URL", "http://logistica-api:8000")
CAUTELA = os.environ.get("CAUTELA_URL", "http://cautela-api:8000")


def placas_visiveis(login):
    resp = httpx.get(f"{CAUTELA}/api/frota/disponivel", headers={"X-Usuario-P4": login})
    resp.raise_for_status()
    return {v["placa"] for v in resp.json()["viaturas"]}


def test_viatura_movida_aparece_imediatamente_para_o_p4_de_destino():
    viaturas = httpx.get(f"{LOGISTICA}/api/viaturas").json()
    viatura = next(v for v in viaturas if v["placa"] == "JKL2T22")
    origem = viatura["id_opm"]
    destino, login_destino = (2, "p4.opm2") if origem != 2 else (3, "p4.opm3")
    assert viatura["placa"] not in placas_visiveis(login_destino)

    try:
        inicio = time.perf_counter()
        resp = httpx.post(f"{LOGISTICA}/api/viaturas/{viatura['id_viatura']}/movimentar",
                          json={"id_opm_destino": destino, "usuario": "teste.e2e"})
        resp.raise_for_status()
        visivel = viatura["placa"] in placas_visiveis(login_destino)
        latencia = time.perf_counter() - inicio
    finally:
        if origem is not None:
            httpx.post(f"{LOGISTICA}/api/viaturas/{viatura['id_viatura']}/movimentar",
                       json={"id_opm_destino": origem, "usuario": "teste.e2e"})

    print(f"\nMovimentação + primeira leitura no Cautela: {latencia * 1000:.0f} ms")
    assert visivel, "a viatura deveria aparecer já na primeira leitura após o commit"
    assert latencia < 5
