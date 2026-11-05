# RAG de exemplos (few-shot dinâmico), 05/11/2026

Evidência dos itens 04 e 06. Só métricas agregadas; nenhum nome de unidade real.

## O que é

Antes de perguntar ao Qwen, o sistema recupera as **associações já conhecidas** mais parecidas na
**forma** com a unidade analisada (ex.: outros "NPM <cidade> - Nº BPM") e as coloca no prompt como
referência de padrão (prompt `v6` = `v2` + exemplos). O modelo aprende o padrão da instituição pelos
exemplos em vez de regras escritas, que o 7B não seguia (ver `ajuste_prompt_20261105.md`, v4).

- **De onde vêm os exemplos:** no sistema, das associações **confirmadas** (nome idêntico ou decisão do
  revisor) para OPM ativa; sugestões pendentes nunca viram exemplo. Na avaliação, do gabarito.
- **Recuperação** (`BancoExemplos`): compara a forma (termos frequentes como NPM/CIA/BPM mantidos,
  números → #, nomes próprios → X), com termos raros em comum como desempate.

## Proteção contra "trapaça" (vazamento)

- Exemplos da avaliação **só da partição dev** (69 pares de alta confiança: pureza 100% e ≥ 2 viaturas);
  medição **só na partição teste** (157 UPMs). Conferido por código: nenhum exemplo da partição teste.
- A própria unidade (ou uma cópia da descrição) nunca entra como exemplo dela mesma (testado).
- k = 5 exemplos e 5 candidatas fixados **antes** de rodar; uma única execução na partição teste.

## Resultado na partição teste (157 UPMs reais)

| Híbrido (regra exata → Qwen → semelhança) | Acertos | Erros | Sem sugestão | Acurácia | Precisão | Latência média (p95) |
|---|---:|---:|---:|---:|---:|---:|
| Regra atual sozinha | 31 | 32 | 94 | 19,7% | 49,2% | — |
| v1, 20 candidatas (inicial) | 69 | 39 | 49 | 43,9% | 63,9% | 2,4 s (3,3 s) |
| v2, 5 candidatas | 100 | 35 | 22 | 63,7% | 74,1% | 2,0 s (2,6 s) |
| **v6 = v2 + RAG (5 exemplos), 5 candidatas** | **112** | **23** | 22 | **71,3%** | **83,0%** | 2,4 s (3,5 s) |

- Erros caem 1/3 (35 → 23) com 12 acertos a mais. Com a OPM certa entre as candidatas, o Qwen acerta
  84,3% (era 74%). Dos 126 casos que a regra atual não acertava, o híbrido resolve 84 (eram 71).

## Achado: com poucos exemplos, o RAG atrapalha

Nos dados fictícios da demo só havia 4 associações confirmadas, todas "Nº BPM - cidade" → "Nº BATALHAO
... - cidade". Com esse banco, a v6 piorou: a 103 ("2ª CIA PM SANTA AURORA - 1º BPM") foi sugerida como o
batalhão de Santa Aurora (o modelo "aprendeu" que a cidade manda) e "CR 12 - SEDE" ficou sem sugestão.

Decisão: o RAG só é usado com **pelo menos 20 associações confirmadas** (`IA_MIN_EXEMPLOS_RAG`); abaixo
disso a chamada usa **exatamente o prompt v2** e registra "prompt v2" na sugestão. A medição real não
muda (banco de 69). Em produção, o banco cresce com as confirmações e, no próximo passo, com os pares
deduzidos do histórico dos veículos (~265 no banco de desenvolvimento).

## Limites

- Exemplos herdam o ruído do gabarito (ex.: "Diretoria de Saúde" → Hospital da PM aparece como exemplo).
- Medição para UPMs com histórico; o alvo real são as ~97 sem histórico.
- Válido para `qwen2.5:7b` no Ollama 0.40; modelo e versão do prompt ficam gravados em cada sugestão.

Relatório completo: `comparativo_*_teste_v6_rag5_c5.md`.
