# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 18:31 por `avaliacao/comparar_regra_x_qwen.py`.

- Prompt: **v6** · partição do gabarito: **dev** · RAG: 5 exemplos por pergunta, de um banco de 69 pares só da partição dev
- Gabarito: **71** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 5 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 10 | 9 | 52 | 14.1% | 52.6% | 26.8% |
| Qwen (qwen2.5:7b) sozinho | 45 | 11 | 15 | 63.4% | 80.4% | 78.9% |
| Híbrido: exata → Qwen → semelhança | 46 | 11 | 14 | 64.8% | 80.7% | 80.3% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **1**, das quais **1 erradas**.
- Situações: `{"SEM_CORRESPONDENCIA": 52, "PENDENTE": 18, "CONFIRMADO": 1}`

## IA (Qwen)

- Resultados: `{"ACEITA": 56, "SEM_CORRESPONDENCIA": 15}`
- Motivos de descarte/falha: `{}`
- Latência por unidade: média 2312 ms, mediana 2091 ms, p95 3371 ms
- OPM correta entre as candidatas enviadas: **85.9%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **73.8%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 61
- Resolvidos pelo híbrido: **38**
- Acertos da regra perdidos no híbrido: 2
- Origem das sugestões do híbrido: `{"qwen": 55, "sem_sugestao": 14, "regra_similaridade": 1, "regra_exata": 1}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
