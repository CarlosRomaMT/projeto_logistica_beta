# Comparativo: regra atual x Qwen local x híbrido

Gerado em 05/11/2026 14:06 por `avaliacao/comparar_regra_x_qwen.py`.

- Gabarito: **228** UPMs reais cuja OPM correta foi deduzida do histórico dos veículos (pureza ≥ 1.0, OPM vigente).
- Candidatas por pergunta à IA: 20 (de 458 OPMs vigentes); confiança mínima 0.6; limiar de semelhança da regra 0.75.
- Os métodos só veem os **nomes**; o gabarito veio dos **códigos**. Nenhum nome aparece neste relatório.

## Resultado

| Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão (acerto/sugeridas) | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual (normalização + difflib) | 41 | 41 | 146 | 18.0% | 50.0% | 36.0% |

## Segurança da regra atual

- Confirmações automáticas (nome igual após normalizar): **6**, das quais **2 erradas**.
- Situações: `{"PENDENTE": 76, "SEM_CORRESPONDENCIA": 146, "CONFIRMADO": 6}`

Toda sugestão (regra ou IA) continua exigindo confirmação humana antes de lotar qualquer viatura; só a igualdade exata do nome é confirmada automaticamente.
