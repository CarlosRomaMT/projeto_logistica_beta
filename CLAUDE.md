# CLAUDE.md

Guia do projeto para quem chega agora (pessoas da equipe e Claude Code): contexto, decisões já tomadas
e o histórico do trabalho. Instruções de execução estão no `README.md`.

## O que é

MVP do projeto final do curso **IA Avançada para Infraestrutura, Dados e Desenvolvimento de TI (SESP-MT)**.
Corrige o vínculo viatura → OPM entre o **Sistema de Logística** e o **Sistema de Cautela**: a Logística
gravava só a coluna antiga de unidade e o Cautela decide a visibilidade pela coluna nova, então a viatura
ficava invisível para o P4 da unidade que a usa.

- `logistica-api/`, `cautela-api/` (FastAPI), `frontend/` (React + Vite), `db/` (schema e dados **fictícios**)
- `avaliacao/`: diagnóstico e avaliação da IA contra o **banco de desenvolvimento real** (somente leitura)
- `evidencias/`: relatórios gerados, só com contagens agregadas
- `dados_reais/`: gabarito com nomes reais de unidades, **fora do git** (cada pessoa gera o seu)

## Mapeamento MVP (fictício) ↔ banco real

| MVP | Banco real |
|---|---|
| `tb_viatura.cd_unidade_legado` | `transporte.tb_veiculo.cod_upm` → `geral.tb_upm` (coluna de nome: `upm`) |
| `tb_viatura.fk_id_opm_unidade` | `transporte.tb_veiculo.cod_opm` → `sgpm.opm` (`opm`, `opm_abreviatura`) |
| `tb_opm.status` ATIVA | `sgpm.opm.vigente = 'S'` |
| status da viatura | `tb_veiculo.cod_situacao` (frota operacional = 1 ATIVO, 2 MANUTENÇÃO, 8 RESERVA) |

O Cautela real filtra a grade do P4 por `tb_veiculo.cod_opm` (OPM do P4 + subordinadas) e o check-in
exige `opm.vigente = 'S'`. Nenhuma das duas colunas de `tb_veiculo` tem FK.

## Regras que não podem ser quebradas

- **Dados:** o banco de desenvolvimento é institucional. Nunca ler placa, chassi, RENAVAM, valor, obs,
  prefixo, contatos, endereço/coordenadas, comandante, proprietário nem colunas `log_*`; nunca `SELECT *`.
  `avaliacao/conexao.py` bloqueia isso antes de executar (e há teste). Conexão sempre somente leitura.
- **Credenciais:** nunca no código nem impressas. A URL vem de `DIAG_DATABASE_URL` ou de um `.env`
  externo (`--env-file`). As senhas do `docker-compose.yml` são fictícias e só locais.
- **Nomes de unidades reais** ficam em `dados_reais/` (ignorado) e só são enviados ao **Ollama local**.
  `evidencias/` só pode ter agregados.
- **IA só sugere.** Nenhuma sugestão (IA ou semelhança) lota viatura sem confirmação humana; só o nome
  igual após normalizar é confirmado automaticamente. Decisões manuais nunca são sobrescritas.
- Toda escrita de lotação passa pelo serviço de movimentação (`logistica-api/app/services/movimentacao.py`).

## Decisões já tomadas

- 2026-10-28: na implantação, viatura cautelada pode mudar de lotação (na operação continua bloqueada).
- 2026-10-29: idem para correção de divergências; confirmação manual do de-para só para OPM ativa.
- 2026-11-05: `sgpm.opm.vigente`: **S = vigente, N = não vigente; E e C são desconsiderados** (nunca
  tratados como vigentes, contados à parte).
- 2026-11-05: IA = **Qwen local via Ollama** (`qwen2.5:7b`), não serviço externo, porque os nomes são
  dados institucionais.

## Histórico

### Semana de 2026-10-26: MVP com dados fictícios
Construído o MVP completo (ver `README.md`): RF01 a RF04, RNF01/RNF02, aba Implantação em 4 etapas
(de-para com validação humana, carga com simulação, correção de divergências, lotação da OPM 0),
histórico, rollback total, 60+ testes com Postgres, e2e e CI.

### 2026-11-05: confronto com os requisitos do curso e com o banco real
1. **Leitura das exigências do MVP final** (10 requisitos obrigatórios). Conclusão: o projeto atendia
   quase tudo, mas **não tinha IA** (o de-para era só normalização + `difflib`), falhando o item 04 e o
   3º cenário do item 06 (falha da IA).
2. **Proposta:** IA no ponto em que a regra falha (sugerir a OPM de uma unidade antiga), com Qwen local,
   saída em JSON Schema, validação determinística, plano B pela regra atual e humano no controle.
3. **Diagnóstico no banco de desenvolvimento** (só agregados):
   - 482 de 2.459 viaturas operacionais (**19,6%**) com lotação quebrada: 172 sem `cod_opm`, 29 com
     `cod_opm` inexistente (invisíveis no Cautela) e 281 em OPM não vigente/desconsiderada (sem check-in).
   - **Não existe chave UPM↔OPM**: `sgpm.opm.cod_upm` tem 6 de 520 preenchidos, todos inválidos.
   - **Ponte melhor que o nome: o histórico dos veículos.** Das 311 UPMs com viaturas nas duas colunas,
     265 têm todas as viaturas numa só OPM. Resolve 133 das 172 viaturas operacionais sem OPM.
   - Relação **N:1** (até 12 UPMs na mesma OPM). Nomes muito diferentes ("NPM Luciara" × "NUCLEO PM -
     LUCIARA", "CR15 - SEDE" × "15º COMANDO REGIONAL").
   - 94 viaturas operacionais divergem da OPM dominante da sua UPM: **não dá para saber qual coluna está
     certa** sem revisão humana.
4. **Implementado:**
   - `logistica-api/app/services/ia_de_para.py`: cliente Ollama, seleção de 20 candidatas (termos raros
     pesam mais), prompt, validação (JSON, id dentro das candidatas, confiança 0–1 e ≥ 0,6), disjuntor
     após 3 falhas. Testes em `logistica-api/tests/test_ia_de_para.py` (Ollama simulado, 15 testes).
   - `avaliacao/`: `diagnostico_real.py`, `gerar_gabarito.py` (UPM→OPM pelo histórico, pureza 100%, OPM
     vigente: 228 UPMs), `comparar_regra_x_qwen.py`, `metricas.py`, `conexao.py`. 16 testes.
   - Job `test:avaliacao` no CI e seção nova no README.
5. **Resultado do comparativo** (228 UPMs reais, só pelos nomes; `evidencias/comparativo_*_completo.md`):

   | Método | Acertos | Erros | Sem sugestão | Acurácia | Precisão |
   |---|---:|---:|---:|---:|---:|
   | Regra atual | 41 | 41 | 146 | 18,0% | 50,0% |
   | Qwen sozinho | 90 | 41 | 97 | 39,5% | 68,7% |
   | Híbrido (exata → Qwen → semelhança) | 100 | 50 | 78 | 43,9% | 66,7% |

   Qwen: 0 respostas fora do contrato em 228, 2,4 s/unidade (RTX 3060), OPM certa entre as candidatas em
   87,7%, mas o modelo responde "nenhuma" com frequência (96 casos). Teste de falha com Ollama fora do ar:
   disjuntor abriu e o híbrido caiu na regra atual (`evidencias/*_falha_ollama.md`).
   **Atenção:** o gabarito mede onde as viaturas estão, não o nome da OPM (ex.: viaturas da UPM
   "Diretoria de Saúde" estão no Hospital da PM), então parte dos "erros" é ruído do gabarito.

6. **IA integrada à etapa 1 da tela** (mesmo dia):
   - `app/services/de_para_ia.py`: analisa só linhas PENDENTE/SEM_CORRESPONDENCIA; resposta ACEITA vira
     sugestão (`metodo = 'IA'`, confiança em `score`), as demais só registram o parecer; nunca confirma,
     nunca move viatura; nenhuma transação aberta durante a chamada ao modelo e o UPDATE só vale se a
     linha ainda aguarda decisão (confirmação feita "enquanto a IA pensava" prevalece).
   - Schema: colunas `ia_*` em `tb_de_para_unidade` e tabela `tb_execucao_ia` (log de toda chamada).
   - API: `GET /api/de-para/ia/status`, `POST /api/de-para/ia/sugerir`, `GET /api/de-para/ia/execucoes`;
     cliente via `Depends(obter_cliente_ia)` (substituído nos testes).
   - Tela: botão "Sugerir com IA", faixa de status da IA, selo "Sugestão da IA" com confiança e
     justificativa, "sugestão da IA aceita" nas confirmadas.
   - `docker-compose.yml`: a API acessa o Ollama da máquina por `host.docker.internal`.
   - 14 testes novos (`tests/test_de_para_ia.py`); suíte da logística: 103 passando.
   - Teste real com Qwen nos dados fictícios: 103 → 3º BPM Sul (confiança 1,0, concorda com a
     semelhança); BPTRAN → "nenhuma" (0,1), embora o Batalhão de Trânsito estivesse entre as candidatas.
7. **Ajuste do prompt** (mesmo dia; detalhes em `evidencias/ajuste_prompt_20261105.md`):
   - Diagnóstico da v1: com a OPM certa entre as candidatas, 77 recusas ("nenhuma corresponde exatamente")
     e confusão com a unidade superior citada após o hífen.
   - Prompts versionados em `ia_de_para.PROMPTS` (v1 a v5), `IA_VERSAO_PROMPT`, identificação
     "modelo (prompt vN)" gravada em cada sugestão; comparativo com `--prompt`, `--candidatas` e
     `--particao dev|teste` (dev = `cod_upm % 10 < 3`, 71 UPMs; teste = 157 UPMs, usada só no fim).
   - Escolhida **v2 com 5 candidatas** (melhor na dev). Descartadas: v3 (campo de análise: mais lenta, sem
     ganho), v4 (regra de tipo detalhada: o 7B não seguiu), v5 (acerta os 3 casos da demo, mas é pior nos
     dados reais).
   - Partição teste, híbrido: v1/20 → 69 acertos, 39 erros (43,9%, precisão 63,9%); **v2/5 → 100 acertos,
     35 erros (63,7%, precisão 74,1%)**, 2,0 s por unidade.
   - Exemplos do prompt só fictícios; teste garante que "BPTRAN" não aparece em nenhum prompt.
   - Suíte: logística 110 testes, avaliação 16.
8. **Dados fictícios com padrões reais** (pedido do usuário: "3º BTL PM → 3º BPM Sul" não existia no
   banco real). `db/02_seed.sql` refeito com cidades inventadas (Santa Aurora, Nova Primavera, Serra
   Dourada, Rio Claro do Norte, Lago Azul, Boa Vista do Sul — diferentes das do prompt) mantendo códigos,
   placas e papéis de cada unidade; OPMs em maiúsculas, sem acento e com `abreviatura` (como
   `sgpm.opm`). Novas unidades 107–110 com os padrões difíceis do banco real: NPM citando a superior,
   núcleo que virou pelotão, "CR 12 - SEDE", unidade elevada a regimento (viaturas KLM1A11–KLM4D44).
   Busca de OPM ignora acento e usa a abreviatura. Agora são 20 viaturas ativas sem a coluna nova.
   Qwen v2 nos fictícios: acerta 103, 106 (BPTRAN) e 109; erra 107 (escolhe a 3ª CIA do 2º BPM, como no
   banco real) e responde "nenhuma" para 108 e 110. Suíte: logística 113, cautela 6.

9. **RAG de exemplos** (mesmo dia; `evidencias/rag_exemplos_20261105.md`):
   - `ia_de_para.BancoExemplos` recupera pares já conhecidos pela FORMA da descrição (termos estruturais
     mantidos, números → #, nomes próprios → X); prompt `v6` = v2 + exemplos. No sistema, exemplos =
     associações CONFIRMADAS para OPM ativa (`de_para_ia.exemplos_confirmados`); pendentes nunca.
   - Avaliação sem vazamento: exemplos só da partição dev (69 pares, pureza 100%, ≥ 2 viaturas), medição
     única na teste com k=5 fixado antes. Híbrido na teste: v2 100 acertos/35 erros (74,1%) →
     **v6 112/23 (83,0%)**, 2,4 s por unidade. `v6` virou o padrão (`IA_VERSAO_PROMPT`).
   - Achado nos dados fictícios: com 4 exemplos (todos "Nº BPM - cidade") o RAG piorou (103 → batalhão da
     cidade). Regra: RAG só com ≥ 20 confirmadas (`IA_MIN_EXEMPLOS_RAG`); abaixo disso usa exatamente o
     prompt v2 (`VERSAO_SEM_EXEMPLOS`) e grava "prompt v2" na sugestão (`RespostaIA.versao_prompt`).
   - Usuário pediu checar CPU/GPU antes da medição: GPU livre (o processo "estranho" era `nvgwls.exe`,
     do serviço NVIDIA Display Container, reiniciando sozinho); RAM livre ~3 GB é o recurso mais apertado.
   - Suíte: logística 121, avaliação 16.

10. **Histórico dos veículos como camada do de-para** (mesmo dia):
   - `de_para.historico_por_unidade`: OPM dominante de cada unidade antiga pelas viaturas que já têm as
     duas colunas (≥ 2, ≥ 80% na mesma OPM ativa, nunca movimentadas pelo sistema novo, fora da OPM 0).
   - Camadas em `sincronizar_de_para`: nome idêntico (CONFIRMADO) → histórico (PENDENTE, `metodo =
     'HISTORICO'`, evidência na observação) → semelhança. Histórico **sugere, não confirma** (ruído real:
     Diretoria de Saúde → Hospital). Nome idêntico com histórico divergente: confirma, mas com aviso.
   - Confirmação em lote pelo revisor: `POST /api/de-para/historico/confirmar` (tudo ou nada) e botão
     "Confirmar sugestões do histórico (N)" na etapa 1; selo "Sugestão pelo histórico".
   - IA não analisa nem sobrescreve linhas HISTORICO. RAG usa confirmadas + histórico com pureza 100%.
   - Seed: 24 unidades já parcialmente migradas (201–224, OPMs 12–35, viaturas HST0101–HST2402) com os
     padrões reais; total 72 viaturas. Com 28 exemplos o RAG fica ligado na demo: a 107 passou a ser
     acertada (NUCLEO PM - RIO CLARO DO NORTE); sem RAG errava para a superior.
   - Seletor de candidatas com componente de sigla (termo desconhecido comparado letra a letra, bônus
     se ≥ 0,75): OPM certa entre as 5 candidatas 83,1% → 85,9% (dev), 80,9% → 81,5% (teste); remedição da
     v6 na teste deu o mesmo resultado (112 acertos, 23 erros, 83,0%).
   - Suíte: logística 128, cautela 6, avaliação 16.
   - **Desfeito no mesmo dia (item 12):** a camada de histórico e o botão de lote foram removidos.
11. **Roteiro no Docker + revisão com o usuário** (mesmo dia): ambiente sobe com
    `POSTGRES_PORTA_HOST=5435` (a 5433 é de outro projeto local, `app_web_conf_dos_sonhos-db-1`); se o
    Postgres reaproveitar volume antigo, rodar `scripts.reset_demo`. `scripts/diagnostico_ia.py` mostra o
    que a IA recebe/responde para unidades específicas.
12. **Decisões do usuário em 05/11/2026 (fim do dia):**
    - **Sem camada "histórico das viaturas":** no banco real, as viaturas com as duas colunas foram
      preenchidas por scripts antigos de equiparação POR DESCRIÇÃO; não é evidência independente. Fluxo:
      nome idêntico → Sugestão da IA (semelhança como plano B) → revisor → divergência vira proposta de
      correção (etapa 3). Seed sem as unidades 201–224 (OPMs 12–35 continuam no cadastro como candidatas).
      Os pares das viaturas continuam como **exemplos do RAG** (`de_para.historico_por_unidade`).
      Consequência: o gabarito mede concordância com aqueles scripts, não a verdade.
    - **Sem unidade antiga associada a OPM inativa no seed** (quase não ocorre em dev/prod): saíram a 105 e
      a EFG1J11; OPM 5 extinta fica só para a demo do RF03; o tratamento continua no código, com teste
      que monta o próprio cenário.
    - **Hierarquia** (`sgpm.opm_tipo_orgao`): CR > BPM ≈ CIPM > CIA > PEL > NPM; **Regimento = Batalhão,
      Esquadrão = Companhia, Esquadrão Independente = CIPM**. Tabelas de classificação têm registros
      "Teste" com códigos aleatórios (9 OPMs vigentes apontam para eles).
    - **Prompt v8 é o padrão** (v7 = subida de nível + "sempre a mais plausível"; v8 = v7 + equivalências):
      teste 116 acertos / 30 erros (79,5%) contra v6 112 / 23 (83,0%); núcleo → pelotão 5 de 5 (eram 2).
      Sem RAG vale `v8s`. Demo sem RAG: 103, 106, 108, 109 certas; 107 e 110 o revisor corrige; com RAG
      as 6 certas. Evidência: `evidencias/ajuste_nivel_20261105.md`.
    - Postgres do compose com porta configurável (`POSTGRES_PORTA_HOST`).
    - Suíte: logística 125, cautela 6, avaliação 16.

13. **Alerta de coerência** (mesmo dia, pedido do usuário após o 107 da demo): o modelo escolheu a
    3ª CIA PM - 2º BPM e justificou "mesma localidade" (falso). `SeletorCandidatas.alerta_de_coerencia`:
    termos distintivos da descrição (IDF ≥ 3, sem palavras de tipo `TERMOS_DE_TIPO`) ausentes na OPM
    sugerida e presentes em outra candidata (≥ 80%) → `tb_de_para_unidade.ia_alerta`, "⚠ Verifique: ..." na
    tela. Não descarta (descartar barrava 6 acertos e 6 erros na teste); com alerta: 9 de 142 sugestões,
    5 erros e 4 acertos. Demo: alerta útil no 107, falso alarme no 103. Métricas `alertas_em_erros` /
    `alertas_em_acertos` no comparativo. Suíte: logística 128, avaliação 17.

14. **Top 3 só na dúvida** (sugestão do usuário): `ia_de_para.alternativas_para_revisor` — sem sugestão
    (ou confiança baixa) ou com alerta, grava em `tb_de_para_unidade.ia_alternativas` as próximas candidatas
    do seletor (até 3 opções com a sugestão); tela mostra "Outras opções" (clique preenche a OPM; revisor
    confirma). Teste: OPM certa na tela 72,6% → 77,7% com alternativas em 24 de 157 linhas (top 3 sempre:
    79,6%). Demo: 107 e 110 resolvidas pela 1ª opção. Comparativo: `certa_entre_opcoes_mostradas`.
    Suíte: logística 133, avaliação 18.
15. **Seed sem a GHI3P33** (pedido do usuário): viatura cautelada com código de unidade inexistente e sem
    OPM não é cenário realista. O teste "etapa 4 lota viatura cautelada, operação continua bloqueando"
    monta o próprio cenário (GHI1N11 cautelada na OPM 0). Agora: 18 viaturas ativas sem OPM; carga = 7
    lotadas, 4 na OPM 0, 1 divergência.

## Próximos passos

1. 107 (núcleo citando a superior) e 110 (esquadrão elevado a regimento) sem RAG na demo: só se resolvem
   com exemplos; considerar exemplos fictícios suficientes no seed se a demo precisar mostrar o RAG.
2. Testar `qwen3:8b` (cabe nos 6 GB da RTX 3060) com `--modelo`, na mesma partição teste. Opcional:
   seletor de candidatas por embeddings locais — a OPM certa está entre as 5 candidatas em ~81% dos casos.
3. Revisar à mão uma amostra dos erros do híbrido (separar erro do método × ruído do gabarito).
4. Etapa de divergências: no banco real não há coluna "certa" presumida; mostrar as duas ao revisor.
5. Documentar para a apresentação: critério de sucesso, desenho da arquitetura e seção de limitações.
   Fine-tuning e MCP foram avaliados e descartados por ora (poucos pares e ruidosos; MCP não melhora a
   qualidade da sugestão).

Testes da logística localmente: se a porta 5433 estiver ocupada, suba um Postgres de teste em outra porta
e aponte `TEST_DATABASE_URL` para ele (`DB_SQL_DIR=../db`).

## Como rodar rápido

```bash
docker compose up -d --build                                   # MVP com dados fictícios
python -m venv .venv && .venv\Scripts\pip install -r logistica-api/requirements.txt
.venv\Scripts\python -m pytest avaliacao/tests                  # sem banco/Ollama
.venv\Scripts\python -m avaliacao.diagnostico_real --env-file <.env com DATABASE_URL>
.venv\Scripts\python -m avaliacao.gerar_gabarito --env-file <.env com DATABASE_URL>
.venv\Scripts\python -m avaliacao.comparar_regra_x_qwen --limite 10 --rotulo teste
```

Convenções: código, mensagens e documentação em português; mensagens de erro compreensíveis para o
usuário final; testes para todo comportamento novo.
