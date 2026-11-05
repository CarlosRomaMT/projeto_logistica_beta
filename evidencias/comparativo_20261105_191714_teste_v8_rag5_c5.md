# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 19:17 por `avaliacao/comparar_regra_x_qwen.py`.

- Prompt: **v8** · partição do gabarito: **teste** · RAG: 5 exemplos por pergunta, de um banco de 69 pares só da partição dev
- Gabarito: **157** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 5 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 31 | 32 | 94 | 19.7% | 49.2% | 40.1% |
| Qwen (qwen2.5:7b) sozinho | 114 | 28 | 15 | 72.6% | 80.3% | 90.4% |
| Híbrido: exata → Qwen → semelhança | 116 | 30 | 11 | 73.9% | 79.5% | 93.0% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **5**, das quais **1 erradas**.
- Situações: `{"PENDENTE": 58, "SEM_CORRESPONDENCIA": 94, "CONFIRMADO": 5}`

## IA (Qwen)

- Resultados: `{"ACEITA": 142, "SEM_CORRESPONDENCIA": 14, "DESCARTADA": 1}`
- Motivos de descarte/falha: `{"ID_FORA_DAS_CANDIDATAS": 1}`
- Latência por unidade: média 2454 ms, mediana 2237 ms, p95 3747 ms
- OPM correta entre as candidatas enviadas: **81.5%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **89.1%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 126
- Resolvidos pelo híbrido: **90**
- Acertos da regra perdidos no híbrido: 5
- Origem das sugestões do híbrido: `{"qwen": 137, "sem_sugestao": 11, "regra_similaridade": 4, "regra_exata": 5}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
