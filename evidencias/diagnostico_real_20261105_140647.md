# Diagnóstico da lotação de viaturas (banco de desenvolvimento)

Gerado em 05/11/2026 14:06 por `avaliacao/diagnostico_real.py`. Conexão somente leitura; apenas contagens agregadas (nenhum nome, placa, chassi, RENAVAM, valor, contato ou log).

## Resumo

- Frota operacional (situações 1, 2, 8): **2459** viaturas
- Com problema de lotação: **482 (19.6%)**
- Invisíveis no Cautela (sem `cod_opm` ou `cod_opm` inexistente): **201**
- O Cautela filtra a grade do P4 por `tb_veiculo.cod_opm` e o check-in exige `opm.vigente = 'S'`.

## Chaves estrangeiras em tb_veiculo.cod_upm / cod_opm

_(nenhuma linha)_

## Volumes

| veiculos | veiculos_operacionais | upms | opms |
|---|---|---|---|
| 6883 | 2459 | 408 | 520 |

## Vigência das OPMs (S = vigente, N = não; E/C desconsideradas)

| vigencia | opms |
|---|---|
| desconsiderada (E/C/outros) | 4 |
| não vigente (N) | 58 |
| vigente (S) | 458 |

## Lotação da frota operacional (situações 1, 2 e 8)

| situacao | viaturas |
|---|---|
| 1. sem cod_opm (invisível no Cautela) | 172 |
| 2. cod_opm inexistente em sgpm.opm (invisível) | 29 |
| 3. OPM não vigente (sem check-in) | 263 |
| 4. OPM com vigência desconsiderada (E/C) | 18 |
| 5. OPM vigente (OK) | 1977 |

## Viaturas sem cod_opm por situação (frota inteira)

| cod_situacao | descricao | viaturas_sem_cod_opm |
|---|---|---|
| 1 | ATIVO | 131 |
| 2 | MANUTENÇÃO PREVENTIVA | 28 |
| 4 | SUBSTITUIDO | 28 |
| 8 | CARRO RESERVA | 13 |
| 9 | INSERVIVEL PARA DESCARGA | 4 |
| 10 | RECOLHIDO | 22 |
| 11 | TRANSFERIDA PARA OUTRA UPM | 1 |

## Integridade referencial (as colunas não têm FK)

| cod_upm_orfao | cod_upm_orfao_operacional | cod_opm_inexistente | cod_opm_inexistente_operacional | sem_nenhuma_lotacao |
|---|---|---|---|---|
| 75 | 13 | 57 | 29 | 0 |

## Ponte existente sgpm.opm.cod_upm

| opms | com_cod_upm | cod_upm_valido |
|---|---|---|
| 520 | 6 | 0 |

## De-para deduzido do histórico: pureza por UPM

| faixa | upms | viaturas |
|---|---|---|
| a. todas as viaturas numa única OPM | 265 | 4680 |
| b. OPM dominante com 80 por cento ou mais | 38 | 1857 |
| c. espalhada | 8 | 119 |

## De-para deduzido: quantas UPMs caem na mesma OPM (relação N:1)

| upms_por_opm | opms |
|---|---|
| 1 | 273 |
| 2 | 24 |
| 3 | 8 |
| 4 | 2 |
| 5 | 1 |
| 7 | 1 |
| 12 | 1 |

## Viaturas sem cod_opm: como cada uma pode ser resolvida

| operacional | resolucao | viaturas |
|---|---|---|
| True | 1. resolvível pelo histórico (confiável) | 117 |
| True | 2. histórico fraco (revisão humana) | 2 |
| True | 3. dominante não vigente (buscar sucessora) | 33 |
| True | 4. UPM sem histórico (alvo da IA por nome) | 12 |
| True | 5. UPM órfã (sem nome: nada resolve) | 8 |
| False | 1. resolvível pelo histórico (confiável) | 8 |
| False | 3. dominante não vigente (buscar sucessora) | 2 |
| False | 4. UPM sem histórico (alvo da IA por nome) | 39 |
| False | 5. UPM órfã (sem nome: nada resolve) | 6 |

## Frota operacional com as duas colunas: OPM atual x OPM dominante da UPM

| comparacao | viaturas |
|---|---|
| DIVERGENTE em UPM confiável | 94 |
| divergente em UPM espalhada | 38 |
| igual à dominante | 2155 |

## UPMs sem nenhuma viatura com as duas colunas (só o nome resolve)

| upms_sem_historico |
|---|
| 98 |

## Qualidade dos nomes (insumo da comparação por nome e da IA)

| tabela | total | nome_vazio | com_sigla | nomes_duplicados |
|---|---|---|---|---|
| geral.tb_upm | 408 | 0 | 6 | 1 |
| sgpm.opm (vigentes) | 458 | 0 | 458 | 2 |
