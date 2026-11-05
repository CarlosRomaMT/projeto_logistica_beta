# Subida de nível das unidades (prompts v7 e v8), 05/11/2026

Evidência dos itens 04 e 06. Só métricas agregadas; nenhum nome de unidade real.

## Problema observado

Na demo, "NPM LAGO AZUL" não foi associado a "1º PELOTAO PM - LAGO AZUL", nem "1º ESQ IND POLICIAMENTO
MONTADO" ao "REGIMENTO DE POLICIAMENTO MONTADO", embora a OPM certa viesse em 1º lugar entre as
candidatas e o RAG trouxesse exemplos do mesmo padrão. O diagnóstico (`scripts/diagnostico_ia.py`) mostrou
o modelo chamando a OPM certa de "a mais próxima" e mesmo assim recusando: o **tipo e o número mudam
quando a unidade sobe de nível** (núcleo sem número vira "1º Pelotão"; esquadrão vira regimento) e o
prompt exigia número compatível. Também lia a abreviatura "1º PEL PM - 2º BPM" (superior da OPM) como
motivo de recusa.

## Hierarquia (sgpm.opm_tipo_orgao, banco de desenvolvimento)

Comando Regional (CR) > Batalhão (BPM) ≈ Companhia Independente (CIPM) > Companhia (CIA) > Pelotão (PEL) >
Núcleo (NPM). Equivalências informadas pela gestão: **Regimento = Batalhão; Esquadrão = Companhia;
Esquadrão Independente = Companhia Independente** (não existem como tipo na tabela). OPMs vigentes por
tipo: 95 núcleos, 53 pelotões, 90 companhias, 32 CIPM, 39 batalhões, 15 CR.
Qualidade de dados: as três tabelas de classificação têm registros de teste com códigos aleatórios
("OPM Teste", "BPM Teste", "Nivel Teste") e 9 OPMs vigentes apontam para eles.

## O que mudou

- **v7** = v6 + hierarquia, regra de subida de nível, leitura correta da abreviatura e "indique sempre a
  candidata mais plausível; a dúvida vai na confiança" (null só sem nada em comum).
- **v8** = v7 + equivalências Regimento/Esquadrão.
- Exemplos do prompt continuam fictícios; teste garante que nenhum caso da demo (BPTRAN, MONTADO, RPMON,
  LAGO AZUL, RIO CLARO, SANTA AURORA, CR 12) aparece em prompt algum.

## Resultado (híbrido; exemplos do RAG só da partição dev)

| Versão | Dev: acertos / erros | Teste: acertos / erros | Teste: sem sugestão | Teste: precisão | Núcleo → pelotão (teste) |
|---|---|---|---:|---:|---|
| v6 | 46 / 11 | 112 / 23 | 22 | 83,0% | 2 de 5 |
| v7 | 50 / 12 | 116 / 30 | 11 | 79,5% | 5 de 5 |
| **v8 (padrão)** | 49 / 13 | **116 / 30** | **11** | 79,5% | **5 de 5** |

- v7/v8 resolvem as subidas de nível e reduzem pela metade os casos sem sugestão, ao custo de mais erros
  por sugestão (precisão 83,0% → 79,5%). A confiança do modelo não separa esses erros (com ≥ 0,95 a
  precisão na dev foi 68,8%), então o limiar ficou em 0,6.
- Decisão: **v8 como padrão** — toda sugestão passa pelo revisor, e uma sugestão errada custa a mesma busca
  que nenhuma sugestão; `IA_VERSAO_PROMPT=v6` volta à versão de maior precisão.

## Demo (Qwen real, dados fictícios)

Com RAG (≥ 20 pares de exemplo, como no banco real): as 6 unidades da demo certas, inclusive 108 e 110.
Sem RAG (o seed fictício só tem 4 associações confirmadas; vale a v8s): 103, 106, 108 e 109 certas; 107
volta a confundir com a superior e 110 fica sem sugestão — o revisor corrige.

## Alerta de coerência (validação determinística da saída)

No 107 da demo o modelo escolheu "3ª CIA PM - 2º BPM" (só coincide no número da superior) e justificou
"mesma localidade e tipo de unidade" — falso: a justificativa do modelo não é prova. Verificação
determinística: termos distintivos da descrição (IDF ≥ 3 no cadastro; palavras de tipo excluídas) ausentes
na OPM sugerida e presentes em outra candidata (≥ 80% do peso) → alerta para o revisor.

Calibrado na dev e aplicado às respostas gravadas da v8 (sem nova execução do modelo):

| Opção | Teste: acertos | Teste: erros | Precisão |
|---|---:|---:|---:|
| v8 sem verificação | 114 | 28 | 80,3% |
| v8 **descartando** quando incoerente | 108 | 22 | 83,1% (barra 6 erros e 6 acertos) |
| **v8 com alerta (adotado)** | 114 | 28 | 80,3%, com alerta em 9 de 142 sugestões: **5 erros** e 4 acertos |

Descartar troca acertos por precisão; o alerta mantém os acertos e aponta ao revisor parte dos erros mais
perigosos (sugestão errada com justificativa convincente). Na demo: alerta útil no 107 e falso alarme no
103 (a cidade da companhia aparece no nome do batalhão) — o revisor confere e mantém.

## Limitação do gabarito (registrada em 05/11/2026)

Os pares "unidade antiga → OPM" das viaturas já preenchidas foram feitos por **scripts antigos de
equiparação por descrição**. O gabarito mede, portanto, a concordância da IA com essa equiparação, não a
verdade; e esses pares não são usados como evidência para sugerir (seria circular), só como exemplos de
padrão no RAG.

Relatórios: `comparativo_*_dev_v6_rag5_c5`, `*_dev_v7_*`, `*_dev_v8_*`, `*_teste_v7_*`, `*_teste_v8_*`.
