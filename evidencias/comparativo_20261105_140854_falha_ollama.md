# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 14:08 por `avaliacao/comparar_regra_x_qwen.py`.

- Gabarito: **5** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 20 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 1 | 1 | 3 | 20.0% | 50.0% | 40.0% |
| Qwen (qwen2.5:7b) sozinho | 0 | 0 | 5 | 0.0% | 0.0% | 0.0% |
| Híbrido: exata → Qwen → semelhança | 1 | 1 | 3 | 20.0% | 50.0% | 40.0% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **0**, das quais **0 erradas**.
- Situações: `{"SEM_CORRESPONDENCIA": 3, "PENDENTE": 2}`

## IA (Qwen)

- Resultados: `{"INDISPONIVEL": 5}`
- Motivos de descarte/falha: `{"SEM_CONEXAO": 3, "DISJUNTOR_ABERTO": 2}`
- Latência por unidade: média 0 ms, mediana 0 ms, p95 0 ms
- OPM correta entre as candidatas enviadas: **100.0%** (teto da IA: se a certa não foi enviada, não há como acertar)
- Acurácia do Qwen quando a OPM correta foi enviada: **0.0%**

## Onde a IA agrega

- Casos que a regra atual não acertava: 4
- Resolvidos pelo híbrido: **0**
- Acertos da regra perdidos no híbrido: 0
- Origem das sugestões do híbrido: `{"sem_sugestao": 3, "regra_similaridade": 2}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
