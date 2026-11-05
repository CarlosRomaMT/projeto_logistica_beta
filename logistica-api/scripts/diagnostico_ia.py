"""Mostra o que a IA recebe e responde para unidades antigas específicas (diagnóstico, não grava nada).

Uso: python -m scripts.diagnostico_ia 108 110
"""

import sys

from sqlalchemy import text

from app.core.db import engine
from app.services import ia_de_para as ia
from app.services.de_para_ia import exemplos_confirmados, opms_candidatas


def main(codigos: list[str]) -> None:
    with engine.connect() as conn:
        descricoes = dict(conn.execute(text("SELECT cd_unidade, ds_unidade FROM tb_unidade_legado")).all())
        seletor = ia.SeletorCandidatas(opms_candidatas(conn))
        exemplos = exemplos_confirmados(conn)
    banco = ia.BancoExemplos(exemplos) if len(exemplos) >= ia.IA_MIN_EXEMPLOS_RAG else None
    cliente = ia.ClienteOllama()
    print(f"Modelo: {cliente.identificacao} | exemplos no banco: {len(exemplos)} (RAG {'ligado' if banco else 'desligado'})")
    for cd in codigos:
        descricao = descricoes[cd]
        candidatas = seletor.selecionar(descricao)
        usados = banco.buscar(descricao, excluir_chave=cd) if banco else []
        print(f"\n=== {cd} {descricao!r}")
        print(ia.montar_mensagem(descricao, candidatas, usados if cliente.usa_exemplos else None))
        r = cliente.sugerir(descricao, candidatas, usados)
        print(f"--> {r.resultado} id={r.id_opm} confianca={r.confianca} | {r.justificativa}")
    cliente.fechar()


if __name__ == "__main__":
    main(sys.argv[1:] or ["108", "110"])
