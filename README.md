# Frota PMMT: lotação de viaturas (MVP)

Primeira versão demonstrável da correção do vínculo viatura → OPM entre o **Sistema de Logística**
e o **Sistema de Cautela**. **Todos os dados, nomes e colunas são fictícios.**

**Problema:** a Logística atualizava só a coluna antiga (`cd_unidade_legado`), e o Cautela decide a
visibilidade pela coluna nova (`fk_id_opm_unidade`). A viatura ficava invisível para o P4 da unidade
que realmente a usa.

## Como rodar

Pré-requisito: Docker Desktop.

```bash
docker compose up -d --build
```

| Serviço | Endereço |
|---|---|
| Interface web (Logística + Cautela lado a lado) | http://localhost:5173 |
| API Logística (Swagger) | http://localhost:8001/docs |
| API Cautela (Swagger) | http://localhost:8002/docs |
| PostgreSQL | `localhost:5433` (usuário/senha/banco: `frota`) |

O banco começa no estado **"antes da correção"**: 19 viaturas ativas só com a coluna antiga.

**Dados fictícios, padrões reais.** Cidades e unidades são inventadas, mas os casos reproduzem o que o
diagnóstico encontrou no banco de desenvolvimento (`evidencias/diagnostico_real_*.md`): OPMs em
maiúsculas e sem acento com abreviatura própria (como `sgpm.opm`), unidade antiga citando a superior
depois do hífen, núcleo que virou pelotão, sede de comando regional, sigla, unidade elevada a regimento,
legado vazio ou inexistente e a divergência entre a coluna antiga e a nova. (Unidade antiga associada a
OPM inativa quase não ocorre no banco real e ficou fora dos dados; a OPM 5, extinta, existe só para a demo
do bloqueio do RF03. O tratamento continua no código e tem teste próprio.)

| Unidade antiga | OPM correta | Como a regra atual classifica |
|---|---|---|
| 101 `1º BPM - SANTA AURORA` e 111 `PRIMEIRO BATALHAO PM SANTA AURORA` | 1º BATALHAO ... - SANTA AURORA | nome igual (automático) |
| 102 `2 B.P.M. NOVA PRIMAVERA` / 104 `1ª CIA IND PM SERRA DOURADA` | OPM 2 / OPM 4 | nome igual (automático) |
| 103 `2ª CIA PM SANTA AURORA - 1º BPM` | 2ª CIA PM - 1º BPM | semelhança 89% (sugestão) |
| 106 `BPTRAN` | BATALHAO DE POLICIA MILITAR DE TRANSITO | sem sugestão (sigla) |
| 107 `NPM RIO CLARO DO NORTE - 2º BPM` | NUCLEO PM - RIO CLARO DO NORTE | sem sugestão (número é da superior) |
| 108 `NPM LAGO AZUL` | 1º PELOTAO PM - LAGO AZUL | sem sugestão (núcleo virou pelotão) |
| 109 `CR 12 - SEDE` | 12º COMANDO REGIONAL | sem sugestão |
| 110 `1º ESQ IND POLICIAMENTO MONTADO` | REGIMENTO DE POLICIAMENTO MONTADO | sem sugestão (unidade elevada) |

## Como a unidade antiga vira OPM

`tb_viatura.cd_unidade_legado` aponta para o cadastro antigo de unidades (`tb_unidade_legado`), que
**não tem chave comum** com `tb_opm`. A única ponte é a **descrição**, que tem abreviações e grafias
diferentes ("1º BPM - SANTA AURORA", "PRIMEIRO BATALHAO PM SANTA AURORA", "1º BATALHAO DE POLICIA MILITAR -
SANTA AURORA").

1. **Normalização** (`app/services/de_para.py`): minúsculas, sem acentos e pontuação, abreviações
   expandidas (BPM, BTL, CIA, IND, PM…), ordinais por extenso em número ("primeiro" → 1), sem "de/da/do".
2. **Comparação:** se os números da unidade diferem (1º x 2º), não há correspondência. Senão, calcula-se a
   semelhança dos termos (0 a 1).
3. **Classificação** em `tb_de_para_unidade`, feita **na subida da `logistica-api`** (e de novo pela
   carga e pelo `de_para gerar`) para as unidades antigas que ainda não têm de-para:
   - **CONFIRMADO / EXATO:** nomes iguais após normalizar, com uma única OPM. É o único caso automático.
   - **PENDENTE / SIMILARIDADE:** semelhança ≥ 0,75. Fica como sugestão até alguém confirmar.
   - Não há camada "histórico das viaturas": no banco real, as viaturas que já têm as duas colunas foram
     preenchidas por scripts antigos de equiparação por descrição, então não são evidência independente
     (seria circular). Esses pares servem só como **exemplos do RAG**. As divergências entre a OPM atual da
     viatura e a associação confirmada viram **proposta de correção** (etapa 3).
   - **SEM_CORRESPONDENCIA:** nada parecido (ex.: a sigla "BPTRAN").
4. **Validação humana** (aba **Implantação**, etapa 1, que já abre com as sugestões, ou por CSV:
   `python -m scripts.de_para gerar` exporta, o revisor preenche `id_opm_confirmada` e roda
   `python -m scripts.de_para importar <arquivo> --usuario <nome>`). Nos dois caminhos a confirmação
   já lota na hora, pelo serviço de movimentação, as viaturas da unidade que estão sem OPM ou na OPM 0.
   Decisões manuais nunca são sobrescritas.
5. **Carga** (aba **Implantação**, etapa 2, ou `scripts.migrar_opm_legado`): usa só de-para
   **confirmado**. O resto vai para a OPM 0 com o motivo e a sugestão no relatório. Validar antes da
   carga deixa menos viaturas na OPM 0; validar depois também funciona (a confirmação as tira de lá).

O dicionário de abreviações e o limiar de 0,75 são **fictícios** e precisam ser calibrados com o
cadastro real e com quem o conhece.

## O que está implementado

| Requisito | Onde | Situação |
|---|---|---|
| RF01: grava só `fk_id_opm_unidade` | `logistica-api/app/services/movimentacao.py` (ponto único de escrita) | ✅ movimentação e criação |
| RF02: visibilidade por JOIN com a OPM do P4 + status disponível | `cautela-api/app/repositories/frota.py` | ✅ |
| RF03: OPM existente e ativa, mensagem oficial | `validar_opm_destino` + `app/errors.py` | ✅ |
| RF04: carga, contingência (OPM 0) e relatório CSV | `app/services/carga.py` + `scripts/migrar_opm_legado.py` | ✅ com simulação (`--dry-run`) |
| Melhoria: carga pela tela (aba Implantação, etapa 2) | `app/api/carga.py` + `frontend/src/pages/CargaLotacao.tsx` | ✅ simular → executar, relatório para baixar com quem executou |
| RF04: de-para unidade antiga → OPM por descrição, com validação humana | `app/services/de_para.py` + `scripts/de_para.py` | ✅ exportação e importação de CSV (aplica na hora) |
| IA: sugestão de OPM por Qwen local (Ollama) na etapa 1, com justificativa, validação, log e plano B | `app/services/ia_de_para.py` + `app/services/de_para_ia.py` + `ValidacaoDePara.tsx` | ✅ só sugere; confirmação continua humana |
| Melhoria: validação do de-para na tela (aba Implantação, etapa 1) | `app/api/de_para.py` + `frontend/src/pages/ValidacaoDePara.tsx` | ✅ confirmação lota as viaturas na hora, com histórico |
| Melhoria: correção em lote das divergências (o bug original nos dados existentes) | `app/services/divergencias.py` + `frontend/src/pages/CorrecaoDivergencias.tsx` | ✅ proposta → decisão humana → movimentação, tudo ou nada |
| RNF01: transação explícita e rollback total | serviço e script | ✅ testes de falha injetada |
| RNF02: busca reativa de OPM, legado oculto, latência | `frontend/src/components/SeletorOpm` + `e2e/` | ✅ banco compartilhado (~30 ms) |

## Roteiro do demo (≈15 min)

O roteiro inteiro roda pela tela, sem terminal. Os comandos equivalentes ficam como alternativa
(rodam a partir da raiz do projeto; use `-T` no `docker compose exec`, sem ele o comando pode travar
quando executado pelo `!` do Claude Code ou por scripts).

**Ordem:** as quatro etapas da aba **Implantação**: validar o de-para (tela **ou** CSV) → carga da
lotação → correção das divergências → lotar as viaturas que ficaram na OPM 0; depois, operação normal. O de-para não precisa ser gerado: a
`logistica-api` cria as sugestões ao subir.

### 1. Mostrar o problema
Abra http://localhost:5173. Na Logística, 21 viaturas (19 ativas e 2 baixadas) aparecem como
*"Sem unidade: invisível no Cautela"*. No Cautela, o `p4.opm2` não vê nenhuma viatura.

Marque **"Demonstração: mostrar unidade do cadastro antigo"** para ver, ao lado de cada viatura, a
unidade antiga (código e descrição). A coluna *Associação com OPM* (o de-para) já mostra 5 unidades
**confirmadas** (nome igual após normalizar), a 103 como **sugestão a confirmar** (2ª CIA PM - 1º BPM,
semelhança 89%) e a 106 a 110 **sem sugestão**: as sugestões foram criadas na subida da API. Essas colunas vêm
de um endpoint de diagnóstico separado (`/api/diagnostico/legado`); a listagem oficial continua sem
o legado (RNF02).

### 2. Etapa 1: associar as unidades antigas às OPMs (de-para)
Abra a aba **Implantação**. Enquanto o **Revisor** no topo estiver vazio, um aviso pede o
preenchimento; clicar numa ação sem ele leva até o campo (sem login no MVP, o nome fica registrado em
cada decisão). Na tela, o termo técnico "de-para" não aparece: o painel *Associar as unidades antigas às
OPMs* mostra "6 unidade(s) aguardando decisão":
- 103 já vem com a sugestão *2ª CIA PM - 1º BPM* (semelhança): clique em **Confirmar**.
  Esperado: "Viaturas lotadas nela: CDE1F11, CDE2G22".
- 106 a 110 não têm sugestão por semelhança: use **Sugerir com IA** (abaixo) ou busque a OPM
  (a busca ignora acentos e aceita a abreviatura: "Trânsito", "Lago Azul", "RPMON") e confirme. Cada
  confirmação lota a viatura da unidade (GHI2O22, KLM1A11, KLM2B22, KLM3C33, KLM4D44).

**Com IA (Qwen local):** a faixa acima da tabela mostra se a IA está pronta ("IA local pronta
(qwen2.5:7b)") ou indisponível. Clique em **Sugerir com IA**: o modelo analisa só as unidades que
aguardam decisão e, para cada uma, devolve OPM, confiança e uma justificativa, que aparecem na coluna
*Situação* com o selo **Sugestão da IA**. Quando a IA discorda da semelhança de nome, a opinião anterior
fica registrada. Nada é gravado nas viaturas: confirmar continua sendo do revisor (na lista de
confirmadas aparece "sugestão da IA aceita"). Cada chamada fica em `tb_execucao_ia`
(`GET /api/de-para/ia/execucoes`: resultado, motivo de descarte e latência). Para mostrar a falha, feche
o Ollama e clique de novo: a tela avisa "IA indisponível" e as sugestões por semelhança continuam.
Requer Ollama na máquina (`ollama pull qwen2.5:7b`); a API no Docker o acessa por
`host.docker.internal:11434` (`OLLAMA_URL`, `OLLAMA_MODELO`, `IA_HABILITADA` no `docker-compose.yml`).
Resultado observado com `qwen2.5:7b` e o prompt padrão `v8` nos dados fictícios. O seed só tem 4
associações confirmadas (< 20), então o RAG fica desligado e vale a `v8s`, registrada em cada sugestão
como "qwen2.5:7b (prompt v8s)". Mostra na demo tanto o ganho quanto o motivo da validação humana:

| Unidade | Sugestão da IA | Alerta de coerência | |
|---|---|---|---|
| 103 `2ª CIA PM SANTA AURORA - 1º BPM` | 2ª CIA PM - 1º BPM (concorda com a semelhança) | ⚠ "AURORA" está no 1º BPM (falso alarme) | ✓ o revisor confere e mantém |
| 106 `BPTRAN` | BATALHAO DE POLICIA MILITAR DE TRANSITO | — | ✓ |
| 108 `NPM LAGO AZUL` | 1º PELOTAO PM - LAGO AZUL (**subida de nível**: núcleo virou pelotão) | — | ✓ |
| 109 `CR 12 - SEDE` | 12º COMANDO REGIONAL | — | ✓ |
| 107 `NPM RIO CLARO DO NORTE - 2º BPM` | 3ª CIA PM - 2º BPM: **errada** (confundiu com a superior; a justificativa do modelo, "mesma localidade", é falsa) | ⚠ "RIO CLARO" está no NUCLEO PM - RIO CLARO DO NORTE | ✗ o revisor troca |
| 110 `1º ESQ IND POLICIAMENTO MONTADO` | "nenhuma corresponde" | — | o revisor busca "Montado" e escolhe o Regimento |

**Alerta de coerência** (determinístico, `SeletorCandidatas.alerta_de_coerencia`): se os termos distintivos
da descrição (raros no cadastro, como o nome da cidade; palavras de tipo como NPM/CIA/BPM não contam) não
aparecem na OPM sugerida mas aparecem em outra candidata, a linha mostra "⚠ Verifique: ...". A justificativa
do modelo não é prova (no 107 ele afirma "mesma localidade" sem ser). O alerta **não descarta**: nos dados
reais, descartar barrava tantos acertos quanto erros; avisando, sinaliza 5 dos 28 erros da partição teste
com 4 falsos alarmes em 142 sugestões.

Com o RAG ligado (≥ 20 pares de exemplo, como no banco real, onde há ~265 pares das viaturas já
preenchidas), as 6 saem certas (`scripts/diagnostico_ia.py`, `evidencias/ajuste_nivel_20261105.md`).

São os mesmos padrões de erro medidos no banco real (`evidencias/ajuste_prompt_20261105.md`). O
resultado pode variar com outra versão do modelo; o modelo e a versão do prompt ficam gravados em cada
sugestão.

Toda associação confirmada tem o botão **Alterar** (inclusive as automáticas). Alterar move para a nova
OPM as viaturas lotadas pela associação anterior que nunca foram movimentadas depois. Sem escolher a
OPM, Confirmar avisa "Escolha a OPM correta da unidade … antes de confirmar".

Cada viatura lotada passa pelo serviço de movimentação (validação do RF03, histórico com tipo
`CORRECAO_DE_PARA`). Na implantação, viatura cautelada também é lotada. OPM inativa é recusada com a
mensagem oficial. Confirmando 103 e 106 a 110, a etapa 2 cai de 19 para 12 viaturas aguardando.

**Alternativa por CSV** (revisão em massa no Excel, passos 2a e 2b):

#### 2a. Exportar e revisar no Excel (`de_para gerar`)
```bash
docker compose exec -T logistica-api python -m scripts.de_para gerar
```
Esperado: `De-para criado para 0 unidade(s) antiga(s)` (já criado na subida) e o caminho do CSV. **Não
altera nenhuma viatura** nem decisão já gravada. Abra `relatorios/de_para_revisao_<data>.csv` no Excel;
as linhas pendentes vêm primeiro. Na última coluna, `id_opm_confirmada`, preencha só as decisões tomadas:

| cd_unidade_legado | Descrição antiga | id_opm_confirmada |
|---|---|---|
| 103 | 2ª CIA PM SANTA AURORA - 1º BPM | `3` |
| 106 | BPTRAN | `6` |

Linhas em branco não são alteradas. Salve como CSV; a importação aceita o arquivo salvo pelo Excel
com `;` ou `,`.

#### 2b. Importar a revisão (`de_para importar`)
```bash
docker compose exec -T logistica-api python -m scripts.de_para importar relatorios/de_para_revisao_<data>.csv --usuario sgt.revisor
```
Esperado: `2 correspondência(s) confirmada(s)` e `Lotadas na OPM confirmada: CDE1F11, CDE2G22, GHI2O22.`
Mesmo efeito da tela (serviço de movimentação, histórico, cautelada também lotada). A importação é tudo ou
nada: com uma OPM inexistente ou inativa, nada é gravado. Decisões manuais nunca são sobrescritas por um
novo `gerar`.

### 3. Etapa 2: carga da lotação
No painel *Carga da lotação* ("12 viatura(s) aguardando"), clique em **Simular**: aparecem os números e
a lista de inconformidades, sem gravar nada. Depois clique em **Executar carga** (o botão só libera após
a simulação, e a tela avisa isso; sem revisor, o clique leva até o campo). Aplica nas viaturas **só** o de-para confirmado; o resto vai
para a OPM 0.

Pelo terminal: `docker compose exec -T logistica-api python -m scripts.migrar_opm_legado --dry-run` e
depois `... migrar_opm_legado --usuario sgt.revisor`.

Esperado: o resumo separa **7 lotadas na OPM correta** (listadas por placa e OPM,
inclusive a BCD2E22, cautelada), **5 na OPM 0** e **1 divergência** (as 6 que precisam de atenção aparecem
com o motivo), e o link
**Baixar relatório das que precisam de atenção (CSV)** (`relatorios/inconformidades_<data>.csv`, com a coluna
`executado_por`). As outras telas recarregam sozinhas:
- nenhuma viatura ativa fica sem OPM; a `ABC1A23` aparece para o `p4.opm1`, a `CDE1F11` para o `p4.opm3`;
  a `GHI2O22` vai para o Batalhão de Trânsito, que não tem P4 cadastrado nos dados fictícios;
- as 5 sem associação utilizável (legado vazio, código inexistente) ficam na
  *OPM 0 - Sem ligação* (visíveis para `p4.contingencia`) e são resolvidas na etapa 4;
- a `JKL1S11`, cujo legado diverge da coluna nova, não é alterada: vira **1 proposta de correção**
  (etapa 3).

Se a carga rodar antes da etapa 1, 12 viaturas vão para a OPM 0; confirmar o de-para depois as tira de
lá na hora, sem rodar a carga de novo. O resultado da carga é um retrato daquele momento ("gravada às
HH:MM"); o que falta resolver aparece nas etapas 3 e 4, que se atualizam sozinhas.

Diferença entre carga e confirmação: a **confirmação** (tela ou CSV) move as viaturas pelo serviço de
movimentação (com histórico e validação da OPM); a **carga** é a ferramenta de implantação em lote
e grava a coluna nova direto, registrando quem executou só no relatório.

### 4. Etapa 3: corrigir as divergências
Em *Corrigir divergências* ("1 proposta(s) em aberto") aparece a `JKL1S11`: OPM atual
*1º BATALHAO ... - SANTA AURORA*, proposta *2º BATALHAO ... - NOVA PRIMAVERA* (pelo cadastro antigo). Marque e clique em
**Aplicar selecionadas** (ou **Rejeitar**). Esperado: "Corrigidas: JKL1S11"; ela passa a aparecer para
o `p4.opm2`.
- Só entram viaturas **nunca movimentadas pelo sistema novo**: depois da implantação o legado fica
  congelado, e uma movimentação legítima não pode ser revertida para ele.
- O lote é tudo ou nada; viatura cautelada pode ser corrigida, baixada aparece como bloqueada e não
  pode ser selecionada; se a viatura mudou de OPM depois da proposta, a aplicação é recusada.
- **Procurar divergências** gera propostas novas (a carga também gera). Uma proposta rejeitada não volta.

### 5. Etapa 4: lotar as viaturas que ficaram sem OPM
O painel *Lotar as viaturas que ficaram sem OPM* lista as viaturas da OPM 0 com o motivo e, quando há,
a OPM sugerida. Escolha a OPM e clique em **Lotar** (histórico com tipo `LOTACAO_IMPLANTACAO`). Viatura
cautelada aparece com o selo "Cautelada: em uso" e também pode ser lotada; o mesmo endpoint só aceita
viatura que está na OPM 0, para não contornar o RF03 da operação. Resolver a unidade na etapa 1 (ex.: associar a 108) tira da lista,
de uma vez, todas as viaturas dela.

### 6. Movimentar pela tela nova
Escolha uma viatura disponível e busque "Primavera" no campo de OPM (2º BPM - Nova Primavera). Ao gravar, ela aparece na hora
para o `p4.opm2` e some da OPM de origem.

### 7. Bloqueio do RF03
Marque *"Demonstração: listar também OPMs inativas"*, escolha o
*5º BATALHAO DE POLICIA MILITAR - BOA VISTA DO SUL* (extinto) e tente movimentar. Ou deixe a OPM em branco. A mensagem
oficial aparece e nada é gravado.

### 8. Rollback e testes automatizados
```bash
docker compose exec -T logistica-api pytest -v
docker compose exec -T cautela-api pytest -v
docker compose run --rm -v ${PWD}/e2e:/e2e logistica-api pytest /e2e -s   # PowerShell
```

### Recomeçar a demonstração
Volta o banco ao estado "antes da correção" (apaga o histórico, as propostas e as decisões do de-para;
as sugestões do de-para são recriadas na hora, como na subida da API):
```bash
docker compose exec -T logistica-api python -m scripts.reset_demo
```

## Estrutura

```
db/                 schema e dados fictícios (carregados na 1ª subida do Postgres)
logistica-api/      FastAPI: movimentação (RF01/RF03/RNF01), busca de OPMs, script RF04
cautela-api/        FastAPI: grade de viaturas do P4 (RF02)
frontend/           React + Vite: aba Operação (Logística + Cautela) e aba Implantação (de-para, carga, divergências)
e2e/                teste ponta a ponta contra o ambiente no ar (latência RNF02)
avaliacao/          diagnóstico no banco de desenvolvimento, gabarito real e comparativo regra x Qwen
evidencias/         relatórios gerados (só agregados, sem nomes): diagnóstico e comparativos
dados_reais/        gabarito e detalhe com nomes de unidades reais (fora do git)
.gitlab-ci.yml      testes dos dois backends (com Postgres) + avaliação + build do frontend
```

## Diagnóstico e avaliação com dados reais (banco de desenvolvimento)

Valida as premissas do MVP contra o banco de desenvolvimento da instituição e mede a IA com um
gabarito real. Mapeamento: `cd_unidade_legado` = `transporte.tb_veiculo.cod_upm` (→ `geral.tb_upm`),
`fk_id_opm_unidade` = `tb_veiculo.cod_opm` (→ `sgpm.opm`). Vigência da OPM: `S` vigente, `N` não
vigente; `E` e `C` são desconsideradas.

**Proteção de dados:** conexão somente leitura (`default_transaction_read_only`), timeout por consulta e
bloqueio, antes de executar, de qualquer SQL que leia coluna protegida (placa, chassi, RENAVAM, valor, obs,
prefixo, contatos, localização, `log_*`) ou use `SELECT *` (`avaliacao/conexao.py`, testado). A URL vem
de `DIAG_DATABASE_URL` ou de um `.env` externo e nunca é impressa. Os relatórios em `evidencias/` só têm
contagens; nomes de unidades ficam em `dados_reais/` (fora do git) e só vão ao **Ollama local**.

```bash
python -m venv .venv && .venv\Scripts\pip install -r logistica-api/requirements.txt
ollama pull qwen2.5:7b                      # Ollama local (GPU opcional)

# 1. Diagnóstico agregado (itens 05/06): evidencias/diagnostico_real_<data>.md/.json
.venv\Scripts\python -m avaliacao.diagnostico_real --env-file <caminho>\.env
# 2. Gabarito UPM -> OPM deduzido do histórico dos veículos: dados_reais/*.csv
.venv\Scripts\python -m avaliacao.gerar_gabarito --env-file <caminho>\.env
# 3. Comparativo regra atual x Qwen x híbrido: evidencias/comparativo_<data>.md/.json
.venv\Scripts\python -m avaliacao.comparar_regra_x_qwen              # ~3 s por UPM numa RTX 3060
.venv\Scripts\python -m avaliacao.comparar_regra_x_qwen --sem-ia     # só a regra atual
.venv\Scripts\python -m avaliacao.comparar_regra_x_qwen --limite 10  # amostra rápida para a demo
# Testes (sem banco e sem Ollama: IA simulada)
.venv\Scripts\python -m pytest avaliacao/tests
cd logistica-api && ..\.venv\Scripts\python -m pytest tests/test_ia_de_para.py
```

**Como o gabarito é montado:** para cada UPM, as viaturas que têm as duas colunas preenchidas; entra no
gabarito a UPM cujas viaturas estão **todas** na mesma OPM vigente (`--pureza-minima` ajusta). Como o
gabarito vem dos **códigos** e os métodos só veem os **nomes**, a comparação é justa.

**IA (`logistica-api/app/services/ia_de_para.py`):** Qwen via Ollama local recebe a descrição antiga e
as 5 OPMs vigentes mais parecidas (seleção determinística por termos raros, ex.: nome da cidade), com
saída obrigatória em JSON Schema, temperatura 0 e seed fixa. O prompt é versionado (`IA_VERSAO_PROMPT`,
padrão `v2`; `--prompt` no comparativo) e a escolha da versão e do número de candidatas foi feita na
partição dev do gabarito e medida na partição teste (`evidencias/ajuste_prompt_20261105.md`: híbrido de
43,9% para 63,7% de acurácia e de 63,9% para 74,1% de precisão). Depois veio a `v6`, que soma o
**RAG de exemplos**: as associações já confirmadas mais parecidas na forma entram no prompt como
referência (`evidencias/rag_exemplos_20261105.md`: na partição teste, precisão de 74,1% para 83,0% e erros
de 35 para 23). Com menos de 20 associações confirmadas (`IA_MIN_EXEMPLOS_RAG`) o RAG fica desligado e a
chamada usa a versão sem RAG (`v2` para a `v6`, `v8s` para a `v8`), registrada na sugestão. O padrão
atual é a **`v8`** = v6 + hierarquia das OPMs (`sgpm.opm_tipo_orgao`), subida de nível (núcleo → pelotão;
esquadrão/companhia → regimento/batalhão, com Regimento = Batalhão e Esquadrão = Companhia) e "indique
sempre a candidata mais plausível" (`evidencias/ajuste_nivel_20261105.md`: na partição teste, 116 acertos
e 30 erros contra 112 e 23 da v6; núcleo → pelotão 5 de 5, eram 2; `IA_VERSAO_PROMPT=v6` volta à versão de
maior precisão). A resposta é validada: JSON no contrato, id
dentro das candidatas enviadas (barra alucinação), confiança entre 0 e 1 e acima do mínimo (0,6). Ollama
fora do ar, timeout ou erro HTTP → resultado `INDISPONIVEL`/`TIMEOUT` e uso da regra atual; após 3
falhas seguidas, um disjuntor para de chamar o modelo. A IA **nunca confirma**: só sugere para o revisor.

**Cenários de teste do item 06 (IA):** esperado (`test_resposta_valida_vira_sugestao_aceita`),
resposta inadequada (JSON inválido, campo ausente, confiança fora da faixa, id fora das candidatas,
instrução embutida na descrição) e indisponibilidade (sem conexão + disjuntor, timeout, modelo não
instalado). Na demonstração ao vivo: fechar o Ollama e rodar o comparativo com `--limite 5`.

**Limitações conhecidas da avaliação:**
- O gabarito mede **onde as viaturas estão lotadas**, não **qual OPM tem aquele nome**. Ex.: viaturas da
  UPM "Diretoria de Saúde" estão todas na OPM do Hospital da PM; a regra que associa ao nome
  "Diretoria de Saúde" conta como erro. Parte dos "erros" de qualquer método é ruído do gabarito, e os
  erros devem ser revisados por amostragem antes de conclusões fortes.
- Só entram no gabarito UPMs com histórico; as ~97 UPMs sem histórico (o alvo real da IA) não têm
  resposta conhecida.
- Resultado do modelo pode variar entre versões do Qwen/Ollama (o modelo fica registrado no relatório).

## Premissas e simplificações do MVP

- **Banco compartilhado** entre os dois sistemas (visibilidade imediata). Se forem bancos separados,
  falta o evento `viatura.movimentada` (fila/webhook) com SLA de 5 s.
- **Login do P4 simulado** pelo cabeçalho `X-Usuario-P4`; em produção vem do SSO/token existente.
- **Schema por SQL de inicialização** (`db/`), em vez de Alembic. Migrar para Alembic antes de
  produção.
- **Status que impedem movimentação:** `BAIXADA` e `CAUTELADA` na operação (aba Operação, RF03);
  na implantação (etapas 1 a 4), só `BAIXADA` (`app/core/config.py`). A validar com o dono da Logística.
- Fluxos de **alteração patrimonial e reativação** ainda não têm endpoint próprio. Quando forem
  criados, devem chamar `validar_opm_destino` e gravar pelo mesmo serviço.
- O frontend roda com o servidor de desenvolvimento do Vite.
- **Aba Implantação sem controle de acesso:** o revisor é um nome digitado. Em produção, autoria vem do
  SSO e a aba (que mostra descrições do cadastro antigo) fica restrita a perfis autorizados (RNF02).
  O painel *Carga da lotação* grava a lotação da frota inteira: em produção, só para o perfil de
  administrador da implantação (ou removido depois dela, ficando o script).
- **Padrões adotados nas decisões pendentes:** nada é aplicado sem decisão humana; na implantação,
  viatura cautelada pode ser lotada e corrigida (decidido em 29/10/2026), mas na operação continua
  bloqueada até a devolução; confirmação manual do de-para só para OPM ativa.
- **Notificações:** cada correção gera uma notificação por viatura; em lote grande, avaliar consolidar.

## Formato da solução: alternativas para discussão

A aplicação web foi mantida porque os dois sistemas já são web (Python + React) e a correção precisa
mudar o **fluxo de escrita** da Logística. Há alternativas a considerar, inclusive combinadas:

| Alternativa | Vantagem | Desvantagem |
|---|---|---|
| **A. Corrigir a aplicação** (este MVP) | Resolve na origem, valida a OPM, mantém o histórico | Exige mexer em todos os fluxos de escrita da Logística |
| **B. Trigger no PostgreSQL** que preenche `fk_id_opm_unidade` quando o legado muda | Correção imediata, sem deploy da Logística | Mantém a escrita no legado (contraria o RF01), esconde regra no banco, sem a mensagem do RF03 |
| **C. View de compatibilidade no Cautela** (`COALESCE(fk, mapa(legado))`) | Zero alteração na Logística | Paliativo: o Cautela continua dependente do legado |
| **D. Integração por eventos/API** entre sistemas separados | Desacopla os sistemas | Mais infraestrutura; necessária só se os bancos forem separados |

Sugestão: **A** como solução definitiva. **B** pode servir como ponte temporária enquanto a A não
chega à produção, se o problema for urgente.
