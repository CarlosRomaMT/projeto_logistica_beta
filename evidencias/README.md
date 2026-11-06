# Evidências

Índice dos registros desta pasta. Todos os relatórios com dados do banco de desenvolvimento trazem **só
contagens e métricas agregadas**; nenhum nome de unidade real, placa ou dado de viatura. Os pares reais
usados na avaliação ficam em `dados_reais/`, fora do git. O resumo dos resultados está em
[`docs/APRESENTACAO.md`](../docs/APRESENTACAO.md), seções 1, 4 e 6.

## Comece por aqui

| Evidência | O que mostra | Requisito |
|---|---|---|
| [`comparativo_20261105_191714_teste_v8_rag5_c5.md`](comparativo_20261105_191714_teste_v8_rag5_c5.md) | **Resultado final** da IA (prompt v8, padrão) na partição **teste** (157 unidades nunca usadas para ajuste) | 04, 06 |
| [`ajuste_nivel_20261105.md`](ajuste_nivel_20261105.md) | Por que a v8 foi escolhida (hierarquia e subida de nível; v8 × v6) | 04 |
| [`ajuste_prompt_20261105.md`](ajuste_prompt_20261105.md) | Evolução do prompt v1 → v5 e do número de candidatas (20 → 10 → 5) | 04 |
| [`rag_exemplos_20261105.md`](rag_exemplos_20261105.md) | Efeito do RAG de exemplos (v6) e por que ele exige ≥ 20 exemplos | 04 |
| [`diagnostico_real_20261105_140647.md`](diagnostico_real_20261105_140647.md) | Tamanho real do problema no banco de desenvolvimento (2.459 viaturas, 19,6% com lotação quebrada) | 01, 05 |
| [`comparativo_20261105_140854_falha_ollama.md`](comparativo_20261105_140854_falha_ollama.md) | Cenário de falha: avaliação com o Ollama fora do ar (a regra continua, nenhuma sugestão da IA) | 06, 08 |
| `testes_logistica.txt`, `testes_cautela.txt`, `testes_avaliacao.txt` | Saída do `pytest -v` das três suítes | 06 |
| [`prints/`](prints) | Capturas da demonstração: `01_problema`, `02_sugestao_ia` (sugestões, alerta e outras opções), `03_confirmacao`, `04_carga`, `05_p4_ve`, `06_ia_indisponivel`, `07_rf03`, `08_execucoes_ia` | 03, 06, 08 |

## Histórico completo das medições

Cada `comparativo_*.md` tem um `.json` com os mesmos números. Gerados por
`avaliacao/comparar_regra_x_qwen.py`. Partições: **dev** (71 unidades, usada para ajustar) e **teste**
(157 unidades, usada só para medir). Sufixos: `vN` = versão do prompt, `cN` = candidatas por pergunta,
`rag5` = até 5 exemplos do RAG.

**1. Primeira avaliação (228 unidades, sem partição)**

| Arquivo | Conteúdo |
|---|---|
| `comparativo_20261105_140658_so_regra` | Só a regra atual (linha de base, sem IA) |
| `comparativo_20261105_140731_amostra10` | Verificação rápida com 10 unidades |
| `comparativo_20261105_140854_falha_ollama` | Mesmo fluxo com o Ollama desligado |
| `comparativo_20261105_141646_completo` | Primeiro prompt (v1, 20 candidatas) nas 228 |

**2. Ajuste na partição dev**

| Arquivo | Conteúdo |
|---|---|
| `comparativo_20261105_161106_dev_v1` | v1, linha de base do ajuste |
| `comparativo_20261105_161404_dev_v2` a `..._162326_dev_v4` | Variações das regras do prompt (v2 escolhida) |
| `comparativo_20261105_162705_dev_v2_c10`, `..._162945_dev_v2_c5` | v2 com 10 e com 5 candidatas (5 escolhidas) |
| `comparativo_20261105_163325_dev_v5_c5` | v5 (descartada) |
| `comparativo_20261105_183105_dev_v6_rag5_c5` | v6 = v2 + RAG |
| `comparativo_20261105_183353_dev_v7_rag5_c5` | v7 = subida de nível |
| `comparativo_20261105_191041_dev_v8_rag5_c5` | v8 = v7 + equivalências (Regimento = Batalhão…) |

**3. Medição na partição teste (cada versão escolhida medida uma vez)**

| Arquivo | Conteúdo |
|---|---|
| `comparativo_20261105_164016_teste_v1_c20` | v1 com 20 candidatas |
| `comparativo_20261105_164537_teste_v2_c5` | v2 com 5 candidatas |
| `comparativo_20261105_171239_teste_v6_rag5_c5` | v6 com RAG (maior precisão: 83,0%) |
| `comparativo_20261105_175231_teste_v6_rag5_c5_seletor_siglas` | v6 com o seletor ajustado para siglas |
| `comparativo_20261105_184038_teste_v7_rag5_c5` | v7 |
| `comparativo_20261105_191714_teste_v8_rag5_c5` | **v8, padrão atual** (73,9% de acurácia, 79,5% de precisão) |
