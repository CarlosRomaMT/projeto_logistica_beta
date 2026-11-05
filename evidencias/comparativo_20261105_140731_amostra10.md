# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 14:07 por `avaliacao/comparar_regra_x_qwen.py`.

- Gabarito: **10** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 20 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 2 | 3 | 5 | 20.0% | 40.0% | 50.0% |
| Qwen (qwen2.5:7b) sozinho | 7 | 1 | 2 | 70.0% | 87.5% | 80.0% |
| Híbrido: exata → Qwen → semelhança | 7 | 1 | 2 | 70.0% | 87.5% | 80.0% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **0**, das quais **0 erradas**.
- Situações: `{"SEM_CORRESPONDENCIA": 5, "PENDENTE": 5}`

## IA (Qwen)

- Resultados: `{"SEM_CORRESPONDENCIA": 2, "ACEITA": 8}`
- Motivos de descarte/falha: `{}`
- Latência por unidade: média 3222 ms, mediana 2178 ms, p95 12437 ms
- OPM correta entre as candidatas enviadas: **100.0%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **70.0%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 8
- Resolvidos pelo híbrido: **5**
- Acertos da regra perdidos no híbrido: 0
- Origem das sugestões do híbrido: `{"sem_sugestao": 2, "qwen": 8}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
