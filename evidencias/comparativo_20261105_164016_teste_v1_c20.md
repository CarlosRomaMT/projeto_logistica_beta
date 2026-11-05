# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 16:40 por `avaliacao/comparar_regra_x_qwen.py`.

- Prompt: **v1** · partição do gabarito: **teste**
- Gabarito: **157** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 20 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 31 | 32 | 94 | 19.7% | 49.2% | 40.1% |
| Qwen (qwen2.5:7b) sozinho | 62 | 33 | 62 | 39.5% | 65.3% | 60.5% |
| Híbrido: exata → Qwen → semelhança | 69 | 39 | 49 | 43.9% | 63.9% | 68.8% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **5**, das quais **1 erradas**.
- Situações: `{"PENDENTE": 58, "SEM_CORRESPONDENCIA": 94, "CONFIRMADO": 5}`

## IA (Qwen)

- Resultados: `{"ACEITA": 95, "SEM_CORRESPONDENCIA": 61, "BAIXA_CONFIANCA": 1}`
- Motivos de descarte/falha: `{}`
- Latência por unidade: média 2429 ms, mediana 2324 ms, p95 3284 ms
- OPM correta entre as candidatas enviadas: **86.6%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **45.6%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 126
- Resolvidos pelo híbrido: **38**
- Acertos da regra perdidos no híbrido: 0
- Origem das sugestões do híbrido: `{"qwen": 92, "sem_sugestao": 49, "regra_similaridade": 11, "regra_exata": 5}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
