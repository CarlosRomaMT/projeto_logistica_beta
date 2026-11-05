# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 14:16 por `avaliacao/comparar_regra_x_qwen.py`.

- Gabarito: **228** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 20 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 41 | 41 | 146 | 18.0% | 50.0% | 36.0% |
| Qwen (qwen2.5:7b) sozinho | 90 | 41 | 97 | 39.5% | 68.7% | 57.5% |
| Híbrido: exata → Qwen → semelhança | 100 | 50 | 78 | 43.9% | 66.7% | 65.8% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **6**, das quais **2 erradas**.
- Situações: `{"PENDENTE": 76, "SEM_CORRESPONDENCIA": 146, "CONFIRMADO": 6}`

## IA (Qwen)

- Resultados: `{"ACEITA": 131, "SEM_CORRESPONDENCIA": 96, "BAIXA_CONFIANCA": 1}`
- Motivos de descarte/falha: `{}`
- Latência por unidade: média 2365 ms, mediana 2276 ms, p95 3126 ms
- OPM correta entre as candidatas enviadas: **87.7%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **45.0%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 187
- Resolvidos pelo híbrido: **60**
- Acertos da regra perdidos no híbrido: 1
- Origem das sugestões do híbrido: `{"qwen": 128, "sem_sugestao": 78, "regra_similaridade": 16, "regra_exata": 6}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
