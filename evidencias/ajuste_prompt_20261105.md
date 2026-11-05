# Ajuste do prompt da IA (Qwen 2.5 7B local), 05/11/2026

Evidência dos itens 04 (uso efetivo de IA, validação da saída) e 06 (testes). Só métricas agregadas;
nenhum nome de unidade real.

## Método

- Gabarito real: 228 UPMs cuja OPM correta foi deduzida do histórico dos veículos (`gerar_gabarito`).
- Divisão fixa e reprodutível (`cod_upm % 10 < 3`): **dev** = 71 UPMs, usadas para ajustar o prompt;
  **teste** = 157 UPMs, usadas **uma única vez**, no fim, para medir a versão escolhida.
- Exemplos do prompt só com unidades **fictícias**; nenhum par do gabarito e nenhum caso da demonstração
  (há teste garantindo que "BPTRAN" não aparece em nenhum prompt).
- Comandos: `python -m avaliacao.comparar_regra_x_qwen --particao dev|teste --prompt vN --candidatas N`.

## Diagnóstico da v1 (avaliação completa)

Com a OPM certa entre as candidatas (200 casos): 90 acertos, **77 recusas** ("nenhuma corresponde
exatamente") e 33 escolhas erradas. Causas: o modelo buscava nome idêntico; confundia a unidade com a
superior citada após o hífen ("NPM <cidade> - Nº BPM" → companhia do Nº BPM); regra de número rígida.

## Iterações na partição dev (71 UPMs; resultado do híbrido)

| Configuração | Acertos | Erros | Sem sugestão | Precisão | Latência | Observação |
|---|---:|---:|---:|---:|---:|---|
| v1, 20 candidatas | 34 | 10 | 27 | 77,3% | 2,3 s | conservadora demais |
| v2, 20 candidatas | 41 | 18 | 12 | 69,5% | 2,4 s | regras reescritas + exemplos fictícios |
| v3, 20 candidatas | 39 | 18 | 14 | 68,4% | 4,0 s | v2 + campo de análise antes da escolha |
| v4, 20 candidatas | 38 | 18 | 15 | 67,9% | — | v2 + regra de tipo detalhada (7B não seguiu) |
| v2, 10 candidatas | 43 | 15 | 13 | 74,1% | — | menos distratores |
| **v2, 5 candidatas** | **44** | **12** | **15** | **78,6%** | 2,1 s | **escolhida** |
| v5, 5 candidatas | 41 | 14 | 16 | 74,5% | — | v2 + regra "sem localidade"; acerta os 3 casos da demo, mas pior nos dados reais |

A v5 foi descartada apesar de acertar todos os casos da demonstração: a escolha segue os dados reais,
não o exemplo da apresentação. Na demo, a 103 continua resolvida pela semelhança de nome (plano B) e a
106 (BPTRAN) passa a ser resolvida pela IA.

Observação: a confiança informada pelo modelo é pouco informativa (concentra em 0,8–0,9); subir o limiar
para 0,9 cortava mais acertos que erros. Limiar mantido em 0,6.

## Resultado final na partição teste (157 UPMs nunca usadas no ajuste)

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão | Latência média (p95) |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 31 | 32 | 94 | 19,7% | 49,2% | — |
| Híbrido com v1, 20 candidatas | 69 | 39 | 49 | 43,9% | 63,9% | 2,4 s (3,3 s) |
| **Híbrido com v2, 5 candidatas** | **100** | **35** | **22** | **63,7%** | **74,1%** | **2,0 s (2,6 s)** |

- +31 acertos (+45%) e −4 erros em relação à v1; dos 126 casos que a regra atual não acertava, o híbrido
  resolve 71 (eram 38). Perde 2 acertos da regra.
- OPM correta entre as 5 candidatas: 80,9% (teto da IA nesta configuração); quando enviada, o Qwen acerta 74%.
- Nenhuma resposta fora do contrato (JSON/id) em todas as execuções.

## Limites desta medição

- Parte dos "erros" é ruído do gabarito (ex.: UPM "Diretoria de Saúde" com viaturas no Hospital da PM);
  a precisão real tende a ser maior.
- A partição teste mede a generalização para UPMs **com** histórico; o alvo real da IA são as ~97 UPMs
  **sem** histórico, cuja resposta não é conhecida.
- Resultado válido para `qwen2.5:7b` no Ollama 0.40; outra versão de modelo exige nova medição
  (o modelo e a versão do prompt ficam registrados em cada sugestão).

Relatórios completos: `comparativo_*_dev_*.md` e `comparativo_*_teste_*.md` nesta pasta.
