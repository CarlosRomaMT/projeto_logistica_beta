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

O banco começa no estado **"antes da correção"**: 16 viaturas ativas só com a coluna antiga.

## Como a unidade antiga vira OPM

`tb_viatura.cd_unidade_legado` aponta para o cadastro antigo de unidades (`tb_unidade_legado`), que
**não tem chave comum** com `tb_opm`. A única ponte é a **descrição**, que tem abreviações e grafias
diferentes ("1º BPM - CENTRO", "PRIMEIRO BATALHAO PM CENTRO", "1º Batalhão de Polícia Militar - Centro").

1. **Normalização** (`app/services/de_para.py`): minúsculas, sem acentos e pontuação, abreviações
   expandidas (BPM, BTL, CIA, IND, PM…), ordinais por extenso em número ("primeiro" → 1), sem "de/da/do".
2. **Comparação:** se os números da unidade diferem (1º x 2º), não há correspondência. Senão, calcula-se a
   semelhança dos termos (0 a 1).
3. **Classificação** em `tb_de_para_unidade`, feita **na subida da `logistica-api`** (e de novo pela
   carga e pelo `de_para gerar`) para as unidades antigas que ainda não têm de-para:
   - **CONFIRMADO / EXATO:** nomes iguais após normalizar, com uma única OPM. É o único caso automático.
   - **PENDENTE / SIMILARIDADE:** semelhança ≥ 0,75. Fica como sugestão até alguém confirmar.
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
Abra http://localhost:5173. Na Logística, 18 viaturas (16 ativas e 2 baixadas) aparecem como
*"Sem unidade: invisível no Cautela"*. No Cautela, o `p4.opm2` não vê nenhuma viatura.

Marque **"Demonstração: mostrar unidade do cadastro antigo"** para ver, ao lado de cada viatura, a
unidade antiga (código e descrição). A coluna *Associação com OPM* (o de-para) já mostra 5 unidades
**confirmadas** (nome igual após normalizar), a 103 como **sugestão a confirmar** (3º BPM - Sul,
semelhança 93%) e a 106 **sem sugestão** (BPTRAN): as sugestões foram criadas na subida da API. Essas colunas vêm
de um endpoint de diagnóstico separado (`/api/diagnostico/legado`); a listagem oficial continua sem
o legado (RNF02).

### 2. Etapa 1: associar as unidades antigas às OPMs (de-para)
Abra a aba **Implantação**. Enquanto o **Revisor** no topo estiver vazio, um aviso pede o
preenchimento; clicar numa ação sem ele leva até o campo (sem login no MVP, o nome fica registrado em
cada decisão). Na tela, o termo técnico "de-para" não aparece: o painel *Associar as unidades antigas às
OPMs* mostra "3 unidade(s) aguardando decisão":
- 103 (3º BTL PM) já vem com a sugestão *3º Batalhão de Polícia Militar - Sul*: clique em **Confirmar**.
  Esperado: "Viaturas lotadas nela: CDE1F11, CDE2G22".
- 106 (BPTRAN) não tem sugestão: busque "Trânsito", escolha o *Batalhão de Polícia Militar de Trânsito*
  e confirme. A GHI2O22 é lotada nele.
- 105 (5º BPM EXTINTO) foi associada automaticamente a uma OPM **inativa** e por isso aparece como
  pendente ("OPM inativa: escolha outra"). Se ninguém souber qual OPM sucedeu a unidade, deixe-a: a
  viatura dela (EFG1J11) vai para a OPM 0 e é lotada na etapa 4.

Toda associação confirmada tem o botão **Alterar** (inclusive as automáticas). Alterar move para a nova
OPM as viaturas lotadas pela associação anterior que nunca foram movimentadas depois. Sem escolher a
OPM, Confirmar avisa "Escolha a OPM correta da unidade … antes de confirmar".

Cada viatura lotada passa pelo serviço de movimentação (validação do RF03, histórico com tipo
`CORRECAO_DE_PARA`). Na implantação, viatura cautelada também é lotada. OPM inativa é recusada com a
mensagem oficial. A etapa 2 cai de 16 para 13 viaturas aguardando.

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
| 103 | 3º BTL PM | `3` |
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
No painel *Carga da lotação* ("13 viatura(s) aguardando"), clique em **Simular**: aparecem os números e
a lista de inconformidades, sem gravar nada. Depois clique em **Executar carga** (o botão só libera após
a simulação, e a tela avisa isso; sem revisor, o clique leva até o campo). Aplica nas viaturas **só** o de-para confirmado; o resto vai
para a OPM 0.

Pelo terminal: `docker compose exec -T logistica-api python -m scripts.migrar_opm_legado --dry-run` e
depois `... migrar_opm_legado --usuario sgt.revisor`.

Esperado (com a 105 pendente): o resumo separa **7 lotadas na OPM correta** (listadas por placa e OPM,
inclusive a BCD2E22, cautelada), **6 na OPM 0** e **1 divergência** (as 7 que precisam de atenção aparecem
com o motivo), e o link
**Baixar relatório das que precisam de atenção (CSV)** (`relatorios/inconformidades_<data>.csv`, com a coluna
`executado_por`). As outras telas recarregam sozinhas:
- nenhuma viatura ativa fica sem OPM; a `ABC1A23` aparece para o `p4.opm1`, a `CDE1F11` para o `p4.opm3`;
  a `GHI2O22` vai para o Batalhão de Trânsito, que não tem P4 cadastrado nos dados fictícios;
- as 6 sem associação utilizável (OPM extinta, legado vazio, código inexistente) ficam na
  *OPM 0 - Sem ligação* (visíveis para `p4.contingencia`) e são resolvidas na etapa 4;
- a `JKL1S11`, cujo legado diverge da coluna nova, não é alterada: vira **1 proposta de correção**
  (etapa 3).

Se a carga rodar antes da etapa 1, 10 viaturas vão para a OPM 0; confirmar o de-para depois as tira de
lá na hora, sem rodar a carga de novo. O resultado da carga é um retrato daquele momento ("gravada às
HH:MM"); o que falta resolver aparece nas etapas 3 e 4, que se atualizam sozinhas.

Diferença entre carga e confirmação: a **confirmação** (tela ou CSV) move as viaturas pelo serviço de
movimentação (com histórico e validação da OPM); a **carga** é a ferramenta de implantação em lote
e grava a coluna nova direto, registrando quem executou só no relatório.

### 4. Etapa 3: corrigir as divergências
Em *Corrigir divergências* ("1 proposta(s) em aberto") aparece a `JKL1S11`: OPM atual
*1º BPM - Centro*, proposta *2º BPM - Norte* (pelo cadastro antigo). Marque e clique em
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
viatura que está na OPM 0, para não contornar o RF03 da operação. Resolver a unidade na etapa 1 (ex.: associar a 105) tira da lista,
de uma vez, todas as viaturas dela.

### 6. Movimentar pela tela nova
Escolha uma viatura disponível e busque "Norte" no campo de OPM. Ao gravar, ela aparece na hora
para o `p4.opm2` e some da OPM de origem.

### 7. Bloqueio do RF03
Marque *"Demonstração: listar também OPMs inativas"*, escolha o
*5º Batalhão de Polícia Militar (extinto)* e tente movimentar. Ou deixe a OPM em branco. A mensagem
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
as 20 OPMs vigentes mais parecidas (seleção determinística por termos raros, ex.: nome da cidade), com
saída obrigatória em JSON Schema, temperatura 0 e seed fixa. A resposta é validada: JSON no contrato, id
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
