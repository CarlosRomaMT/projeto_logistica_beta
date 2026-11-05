"""RF04: carga que preenche fk_id_opm_unidade a partir do cd_unidade_legado.

Uso (dentro do container logistica-api):
    python -m scripts.migrar_opm_legado --dry-run
    python -m scripts.migrar_opm_legado --usuario fulano

A mesma carga pode ser simulada e executada pela tela (aba Implantação, etapa 2 "Carga da lotação").
As regras estão em app/services/carga.py.
"""

import argparse
from pathlib import Path

from app.services.carga import DIR_RELATORIOS, executar_migracao


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="simula e desfaz tudo ao final")
    parser.add_argument("--saida", type=Path, default=DIR_RELATORIOS, help="pasta do relatório CSV")
    parser.add_argument("--usuario", default="terminal", help="quem executou (vai para o relatório)")
    args = parser.parse_args()

    resultado = executar_migracao(args.dry_run, args.saida, args.usuario)

    print("SIMULAÇÃO (--dry-run): nenhuma alteração foi gravada." if args.dry_run else "Carga concluída.")
    print(f"De-para criados para unidades novas: {resultado.de_para_criados}")
    print(f"Viaturas com lotação alterada:       {resultado.atualizadas}")
    print(f"  lotadas na OPM do de-para:         {len(resultado.lotadas)}")
    print(f"Viaturas na OPM de contingência:     {resultado.contingencia}")
    print(f"Propostas de correção criadas:       {resultado.propostas_criadas}")
    print(f"Inconformidades para auditoria:      {len(resultado.inconformidades)}")
    for item in resultado.inconformidades:
        sugestao = f" (sugestão: {item['opm_sugerida']})" if item.get("opm_sugerida") else ""
        print(f"  - {item['placa']:<8} legado={item['cd_unidade_legado']!r:<6} {item['motivo']}{sugestao}")
    if resultado.relatorio:
        print(f"Relatório: {resultado.relatorio}")
    if resultado.propostas_criadas and not args.dry_run:
        print("Revise as propostas de correção na aba Implantação, etapa 3 (http://localhost:5173).")


if __name__ == "__main__":
    main()
