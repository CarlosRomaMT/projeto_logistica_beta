"""Erros de domínio. As rotas convertem em respostas HTTP pelo handler do main.py."""

# Texto exato exigido pelo RF03.
MSG_OPM_INVALIDA = (
    "Seleção inválida: A OPM de destino deve estar ativa no cadastro corporativo da PMMT."
)


class ErroDominio(Exception):
    status_code = 422

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class OpmInvalida(ErroDominio):
    def __init__(self):
        super().__init__(MSG_OPM_INVALIDA)


class ViaturaNaoEncontrada(ErroDominio):
    status_code = 404

    def __init__(self, id_viatura: int):
        super().__init__(f"Viatura {id_viatura} não encontrada.")


class StatusNaoPermiteMovimentacao(ErroDominio):
    status_code = 409

    def __init__(self, status: str):
        super().__init__(f"Movimentação não permitida: a viatura está com status {status}.")


class DeParaNaoEncontrado(ErroDominio):
    status_code = 404

    def __init__(self, cd_unidade: str):
        super().__init__(f"Unidade antiga {cd_unidade} não está no de-para.")


class PropostaInvalida(ErroDominio):
    status_code = 409


class PlacaDuplicada(ErroDominio):
    status_code = 409

    def __init__(self, placa: str):
        super().__init__(f"Já existe viatura cadastrada com a placa {placa}.")


class RelatorioNaoEncontrado(ErroDominio):
    status_code = 404

    def __init__(self, nome: str):
        super().__init__(f"Relatório {nome} não encontrado.")


class ViaturaForaDaContingencia(ErroDominio):
    status_code = 409

    def __init__(self, placa: str):
        super().__init__(f"A viatura {placa} não está mais na OPM 0; atualize a tela.")
