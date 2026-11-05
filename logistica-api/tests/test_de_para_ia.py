"""IA no fluxo do de-para (etapa 1): sugere, registra e nunca decide. Ollama sempre simulado."""

import json

import httpx
import pytest

from app.api.de_para import MSG_IA_DESATIVADA, obter_cliente_ia
from app.core.db import engine
from app.main import app
from app.services import ia_de_para as ia
from app.services.de_para import sincronizar_de_para

# Na subida, 103 fica PENDENTE por semelhança (OPM 3); 106 (sigla), 107 (núcleo citando a superior),
# 108 (núcleo que virou pelotão), 109 (sede de CR) e 110 (unidade elevada) ficam SEM_CORRESPONDENCIA.
D103 = "2ª CIA PM SANTA AURORA - 1º BPM"
AGUARDANDO = 6


class IaFalsa:
    """Responde por descrição; guarda as candidatas recebidas."""

    modelo = "qwen-falso"
    desligado = False

    def __init__(self, respostas: dict, ao_chamar=None):
        self.respostas = respostas
        self.ao_chamar = ao_chamar
        self.candidatas: dict[str, list[int]] = {}

    def sugerir(self, descricao, candidatas):
        self.candidatas[descricao] = [c.id_opm for c in candidatas]
        if self.ao_chamar:
            self.ao_chamar(descricao)
        return self.respostas.get(descricao, ia.RespostaIA(ia.SEM_CORRESPONDENCIA, confianca=0.9,
                                                           justificativa="nenhuma parecida"))


def aceita(id_opm, confianca=0.85, justificativa="sigla corresponde ao nome"):
    return ia.RespostaIA(ia.ACEITA, id_opm=id_opm, confianca=confianca, justificativa=justificativa, latencia_ms=7)


def ollama(tratar) -> ia.ClienteOllama:
    return ia.ClienteOllama(modelo="qwen2.5:7b", transport=httpx.MockTransport(tratar))


@pytest.fixture(autouse=True)
def de_para_sincronizado():
    with engine.begin() as conn:
        sincronizar_de_para(conn)
    yield
    app.dependency_overrides.pop(obter_cliente_ia, None)


def usar_ia(cliente):
    app.dependency_overrides[obter_cliente_ia] = lambda: cliente
    return cliente


def de_para(client, cd):
    return next(d for d in client.get("/api/de-para").json() if d["cd_unidade_legado"] == cd)


def sugerir(client, usuario="sgt.revisor"):
    return client.post("/api/de-para/ia/sugerir", json={"usuario": usuario})


# 1. Funcionamento esperado


def test_ia_sugere_mas_nao_confirma_nem_move_viatura(client, viatura, consultar):
    usar_ia(IaFalsa({"BPTRAN": aceita(6), D103: aceita(3)}))

    resp = sugerir(client)

    assert resp.status_code == 200
    corpo = resp.json()
    assert (corpo["analisadas"], corpo["sugestoes_novas"], corpo["ia_disponivel"]) == (AGUARDANDO, 2, True)
    assert "2 sugestão(ões) nova(s)" in corpo["mensagem"]
    bptran = de_para(client, "106")
    assert (bptran["situacao"], bptran["metodo"], bptran["id_opm"]) == ("PENDENTE", "IA", 6)
    assert (bptran["ia_resultado"], bptran["ia_modelo"]) == ("ACEITA", "qwen-falso")
    assert bptran["ia_justificativa"] == "sigla corresponde ao nome"
    assert de_para(client, "103")["observacao"] == "IA e semelhança de nome indicam a mesma OPM."
    # Só sugestão: nenhuma viatura mudou e nada foi para o histórico.
    assert viatura("GHI2O22")["fk_id_opm_unidade"] is None
    assert consultar("SELECT count(*) AS n FROM tb_historico_movimentacao")[0]["n"] == 0
    execucoes = consultar("SELECT cd_unidade_legado, resultado, usuario FROM tb_execucao_ia ORDER BY id")
    assert len(execucoes) == AGUARDANDO  # toda chamada fica registrada
    assert [tuple(e.values()) for e in execucoes if e["resultado"] == "ACEITA"] == [
        ("103", "ACEITA", "sgt.revisor"), ("106", "ACEITA", "sgt.revisor")]


def test_quando_a_ia_discorda_a_opiniao_da_semelhanca_fica_registrada(client):
    usar_ia(IaFalsa({D103: aceita(2)}))

    sugerir(client)

    linha = de_para(client, "103")
    assert (linha["metodo"], linha["id_opm"]) == ("IA", 2)
    assert linha["observacao"].startswith("A semelhança de nome indicava: 2ª CIA PM - 1º BPM")


def test_confirmar_a_sugestao_da_ia_lota_as_viaturas_pelo_fluxo_normal(client, viatura, consultar):
    usar_ia(IaFalsa({"BPTRAN": aceita(6)}))
    sugerir(client)

    corpo = client.post("/api/de-para/106/confirmar", json={"id_opm": 6, "usuario": "sgt.revisor"}).json()

    assert corpo["movidas"] == ["GHI2O22"]
    assert (corpo["de_para"]["metodo"], corpo["de_para"]["ia_id_opm"]) == ("MANUAL", 6)  # auditoria
    assert viatura("GHI2O22")["fk_id_opm_unidade"] == 6
    historico = consultar("SELECT tipo, usuario FROM tb_historico_movimentacao")
    assert [tuple(h.values()) for h in historico] == [("CORRECAO_DE_PARA", "sgt.revisor")]


def test_candidatas_sao_so_opms_ativas_sem_a_contingencia(client):
    falsa = usar_ia(IaFalsa({}))

    sugerir(client)

    assert len(falsa.candidatas) == AGUARDANDO
    for ids in falsa.candidatas.values():
        assert len(ids) <= ia.IA_MAX_CANDIDATAS and not {0, 5} & set(ids)  # sem a OPM 0 e sem a 5 (inativa)
    assert 6 in falsa.candidatas["BPTRAN"] and 11 in falsa.candidatas["1º ESQ IND POLICIAMENTO MONTADO"]


def test_ia_que_responde_nenhuma_mantem_a_linha_sem_sugestao(client):
    usar_ia(IaFalsa({}))

    corpo = sugerir(client).json()

    assert corpo["sem_correspondencia"] == AGUARDANDO
    linha = de_para(client, "106")
    assert (linha["situacao"], linha["id_opm"], linha["ia_resultado"]) == ("SEM_CORRESPONDENCIA", None,
                                                                           "SEM_CORRESPONDENCIA")
    assert de_para(client, "103")["metodo"] == "SIMILARIDADE"  # a sugestão por semelhança continua


def test_rag_usa_so_associacoes_confirmadas_para_opm_ativa(client, monkeypatch):
    monkeypatch.setattr(ia, "IA_MIN_EXEMPLOS_RAG", 1)  # banco fictício é pequeno
    mensagens = {}

    def tratar(request):
        conteudo = json.loads(request.content)["messages"][1]["content"]
        descricao = json.loads(conteudo.split("cadastro antigo: ", 1)[1].split("\n", 1)[0])
        mensagens[descricao] = conteudo
        return httpx.Response(200, json={"message": {"content": json.dumps(
            {"id_opm": None, "confianca": 0.5, "justificativa": "teste"})}})

    client.post("/api/de-para/103/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"})  # decisão humana
    usar_ia(ia.ClienteOllama(modelo="qwen2.5:7b", transport=httpx.MockTransport(tratar), versao_prompt="v6"))

    sugerir(client)

    referencia = mensagens["NPM RIO CLARO DO NORTE - 2º BPM"].split("Descrição da unidade", 1)[0]
    assert "ASSOCIAÇÕES JÁ CONFIRMADAS" in referencia
    assert '"2ª CIA PM SANTA AURORA - 1º BPM" → "2ª CIA PM - 1º BPM"' in referencia  # confirmada à mão
    assert "BOA VISTA DO SUL" not in referencia  # 105: confirmada, mas para OPM inativa
    assert "BPTRAN" not in referencia and "LAGO AZUL" not in referencia  # pendentes não viram exemplo
    assert "NPM RIO CLARO DO NORTE" not in referencia  # nunca a própria unidade


def test_rag_fica_desligado_com_poucas_associacoes_confirmadas(client):
    # Só 4 associações confirmadas (nome idêntico) < mínimo: exemplos pouco representativos atrapalham.
    mensagens = []

    def tratar(request):
        mensagens.append(json.loads(request.content)["messages"][1]["content"])
        return httpx.Response(200, json={"message": {"content": json.dumps(
            {"id_opm": None, "confianca": 0.5, "justificativa": "teste"})}})

    usar_ia(ia.ClienteOllama(modelo="qwen2.5:7b", transport=httpx.MockTransport(tratar), versao_prompt="v6"))

    sugerir(client)

    assert len(mensagens) == AGUARDANDO
    assert not any("ASSOCIAÇÕES JÁ CONFIRMADAS" in m for m in mensagens)


# 2. Entrada inválida / resposta inadequada da IA


def test_resposta_fora_do_contrato_e_descartada_e_a_semelhanca_continua(client):
    usar_ia(ollama(lambda req: httpx.Response(200, json={"message": {"content": json.dumps(
        {"id_opm": 999, "confianca": 0.99, "justificativa": "inventei"})}})))

    corpo = sugerir(client).json()

    assert corpo["descartadas"] == AGUARDANDO
    assert "descartada(s) pela validação" in corpo["mensagem"]
    linha = de_para(client, "103")
    assert (linha["metodo"], linha["id_opm"], linha["ia_resultado"]) == ("SIMILARIDADE", 3, "DESCARTADA")
    assert linha["ia_justificativa"] == "Resposta descartada: ID_FORA_DAS_CANDIDATAS"


def test_sugerir_exige_revisor(client):
    usar_ia(IaFalsa({}))
    assert sugerir(client, usuario="").status_code == 422


def test_ia_nunca_altera_decisao_humana(client):
    client.post("/api/de-para/103/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"})
    usar_ia(IaFalsa({D103: aceita(2)}))

    corpo = sugerir(client).json()

    assert corpo["analisadas"] == AGUARDANDO - 1  # a 103 já tinha decisão humana
    assert (de_para(client, "103")["situacao"], de_para(client, "103")["id_opm"]) == ("CONFIRMADO", 3)


def test_confirmacao_feita_enquanto_a_ia_pensava_prevalece(client):
    def revisor_confirma_antes(descricao):
        if descricao == D103:
            client.post("/api/de-para/103/confirmar", json={"id_opm": 3, "usuario": "sgt.revisor"})

    usar_ia(IaFalsa({D103: aceita(2)}, ao_chamar=revisor_confirma_antes))

    sugerir(client)

    linha = de_para(client, "103")
    assert (linha["situacao"], linha["metodo"], linha["id_opm"], linha["ia_resultado"]) == (
        "CONFIRMADO", "MANUAL", 3, None)


# 3. Falha / indisponibilidade da IA


def test_ia_fora_do_ar_avisa_registra_e_mantem_as_sugestoes(client, consultar):
    def recusar(request):
        raise httpx.ConnectError("conexão recusada", request=request)

    usar_ia(ollama(recusar))

    resp = sugerir(client)

    assert resp.status_code == 200
    corpo = resp.json()
    assert (corpo["ia_disponivel"], corpo["falhas"]) == (False, AGUARDANDO)
    assert corpo["mensagem"].startswith("IA indisponível (qwen2.5:7b)")
    assert (de_para(client, "103")["metodo"], de_para(client, "103")["ia_resultado"]) == ("SIMILARIDADE", None)
    registros = consultar("SELECT resultado, motivo FROM tb_execucao_ia ORDER BY id")
    # 3 tentativas reais; depois o disjuntor abre e as demais nem chamam o Ollama.
    assert [tuple(r.values()) for r in registros] == (
        [("INDISPONIVEL", "SEM_CONEXAO")] * 3 + [("INDISPONIVEL", "DISJUNTOR_ABERTO")] * (AGUARDANDO - 3))
    assert client.get("/api/de-para/ia/execucoes").json()[0]["motivo"] == "DISJUNTOR_ABERTO"


def test_ia_desativada_na_configuracao(client):
    usar_ia(None)

    assert sugerir(client).json()["mensagem"] == MSG_IA_DESATIVADA
    assert client.get("/api/de-para/ia/status").json()["habilitada"] is False


@pytest.mark.parametrize("tratar, disponivel, motivo", [
    (lambda r: httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]}), True, None),
    (lambda r: httpx.Response(200, json={"models": [{"name": "outro:1b"}]}), False,
     "O modelo qwen2.5:7b não está instalado no Ollama."),
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("x", request=r)), False,
     "O serviço de IA (Ollama) não respondeu."),
])
def test_status_da_ia_para_o_aviso_da_tela(client, tratar, disponivel, motivo):
    usar_ia(ollama(tratar))

    corpo = client.get("/api/de-para/ia/status").json()

    assert (corpo["habilitada"], corpo["disponivel"], corpo["motivo"]) == (True, disponivel, motivo)
