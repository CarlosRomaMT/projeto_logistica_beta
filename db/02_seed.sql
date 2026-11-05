-- Dados FICTÍCIOS (cidades e unidades inventadas) que reproduzem os padrões encontrados no banco de
-- desenvolvimento (05/11/2026): núcleo citando a unidade superior, núcleo que virou pelotão, sede de
-- comando regional, sigla, unidade elevada/renomeada, OPM extinta, legado vazio ou inexistente e a
-- divergência entre a coluna antiga e a nova. Nomes das OPMs em maiúsculas e sem acento, como em sgpm.opm.

INSERT INTO tb_opm (id_opm, nome, abreviatura, status) VALUES
    (0,  'OPM 0 - SEM LIGACAO (CONTINGENCIA)',                             'OPM 0',                    'ATIVA'),
    (1,  '1º BATALHAO DE POLICIA MILITAR - SANTA AURORA',                  '1º BPM - SANTA AURORA',    'ATIVA'),
    (2,  '2º BATALHAO DE POLICIA MILITAR - NOVA PRIMAVERA',                '2º BPM - NOVA PRIMAVERA',  'ATIVA'),
    (3,  '2ª CIA PM - 1º BPM',                                             '2ª CIA PM - 1º BPM',       'ATIVA'),
    (4,  '1ª COMPANHIA INDEPENDENTE DE POLICIA MILITAR - SERRA DOURADA',   '1ª CIPM - SERRA DOURADA',  'ATIVA'),
    (5,  '5º BATALHAO DE POLICIA MILITAR - BOA VISTA DO SUL',              '5º BPM - EXTINTO',         'INATIVA'),
    (6,  'BATALHAO DE POLICIA MILITAR DE TRANSITO',                        'BPMTRAN - CESP',           'ATIVA'),
    (7,  'NUCLEO PM - RIO CLARO DO NORTE',                                 'NPM - RIO CLARO DO NORTE', 'ATIVA'),
    (8,  '1º PELOTAO PM - LAGO AZUL',                                      '1º PEL PM - 2º BPM',       'ATIVA'),
    (9,  '12º COMANDO REGIONAL',                                           '12º CR',                   'ATIVA'),
    (10, '3ª CIA PM - 2º BPM',                                             '3ª CIA PM - 2º BPM',       'ATIVA'),
    (11, 'REGIMENTO DE POLICIAMENTO MONTADO',                              'RPMON - CESP',             'ATIVA');

-- Cadastro antigo (como geral.tb_upm): abreviado, com grafias diferentes para a mesma unidade e,
-- muitas vezes, citando a unidade superior depois do hífen.
INSERT INTO tb_unidade_legado (cd_unidade, ds_unidade) VALUES
    ('101', '1º BPM - SANTA AURORA'),               -- igual à OPM 1 após normalizar
    ('111', 'PRIMEIRO BATALHAO PM SANTA AURORA'),   -- outra grafia da OPM 1 (relação N:1)
    ('102', '2 B.P.M. NOVA PRIMAVERA'),             -- igual à OPM 2 após normalizar
    ('103', '2ª CIA PM SANTA AURORA - 1º BPM'),     -- companhia com a cidade no meio: semelhança (pendente)
    ('104', '1ª CIA IND PM SERRA DOURADA'),         -- igual à OPM 4 após normalizar
    ('105', '5º BPM - BOA VISTA DO SUL'),           -- corresponde a uma OPM extinta (inativa)
    ('106', 'BPTRAN'),                              -- sigla: sem correspondência por semelhança
    ('107', 'NPM RIO CLARO DO NORTE - 2º BPM'),     -- núcleo citando a superior: OPM 7, não a 2ª/3ª CIA
    ('108', 'NPM LAGO AZUL'),                       -- núcleo que virou pelotão: OPM 8
    ('109', 'CR 12 - SEDE'),                        -- sede de comando regional: OPM 9
    ('110', '1º ESQ IND POLICIAMENTO MONTADO');      -- unidade elevada a regimento: OPM 11

INSERT INTO tb_viatura (placa, modelo, status_operacional, cd_unidade_legado, fk_id_opm_unidade) VALUES
    -- Unidade antiga com correspondência exata: resolvidas pela carga (RF04).
    ('ABC1A23', 'Toyota Hilux',      'DISPONIVEL', '101', NULL),
    ('ABC2B34', 'Chevrolet S10',     'DISPONIVEL', '111', NULL),
    ('ABC3C45', 'Renault Duster',    'MANUTENCAO', '101', NULL),
    ('BCD1D11', 'Toyota Hilux',      'DISPONIVEL', '102', NULL),
    ('BCD2E22', 'Mitsubishi L200',   'CAUTELADA',  '102', NULL),
    ('DEF1H11', 'Ford Ranger',       'DISPONIVEL', '104', NULL),
    ('DEF2I22', 'Chevrolet S10',     'MANUTENCAO', '104', NULL),
    -- Correspondência só por semelhança: contingência até validação humana.
    ('CDE1F11', 'Chevrolet Spin',    'DISPONIVEL', '103', NULL),
    ('CDE2G22', 'Toyota Hilux',      'DISPONIVEL', '103', NULL),
    -- Unidade antiga corresponde a OPM extinta: contingência.
    ('EFG1J11', 'Renault Duster',    'DISPONIVEL', '105', NULL),
    -- Legado nulo ou vazio: contingência.
    ('FGH1K11', 'Toyota Corolla',    'DISPONIVEL', NULL,  NULL),
    ('FGH2L22', 'Toyota Corolla',    'DISPONIVEL', '',    NULL),
    ('FGH3M33', 'Chevrolet Spin',    'MANUTENCAO', NULL,  NULL),
    -- Código inexistente no cadastro antigo (UPM órfã): contingência.
    ('GHI1N11', 'Ford Ranger',       'DISPONIVEL', '999', NULL),
    ('GHI3P33', 'Toyota Hilux',      'CAUTELADA',  '000', NULL),
    -- Sem correspondência por semelhança (alvo da IA): contingência até alguém decidir.
    ('GHI2O22', 'Mitsubishi L200',   'DISPONIVEL', '106', NULL),
    ('KLM1A11', 'Toyota Hilux',      'DISPONIVEL', '107', NULL),
    ('KLM2B22', 'Chevrolet S10',     'DISPONIVEL', '108', NULL),
    ('KLM3C33', 'Renault Duster',    'MANUTENCAO', '109', NULL),
    ('KLM4D44', 'Mitsubishi L200',   'DISPONIVEL', '110', NULL),
    -- Baixadas: não são "ativas", a carga não mexe.
    ('HIJ1Q11', 'Fiat Palio',        'BAIXADA',    '101', NULL),
    ('HIJ2R22', 'Fiat Palio',        'BAIXADA',    '102', NULL),
    -- Já no padrão novo. A primeira mostra o bug original: a Logística antiga
    -- mudou só o legado (para 102) e a coluna nova ficou na OPM 1.
    ('JKL1S11', 'Toyota Hilux',      'DISPONIVEL', '102', 1),
    ('JKL2T22', 'Chevrolet S10',     'DISPONIVEL', '103', 3);

INSERT INTO tb_usuario_p4 (login, nome, fk_id_opm) VALUES
    ('p4.opm1',         'Cap. Fictício Um',     1),
    ('p4.opm2',         'Cap. Fictício Dois',   2),
    ('p4.opm3',         'Cap. Fictício Três',   3),
    ('p4.opm4',         'Ten. Fictício Quatro', 4),
    ('p4.contingencia', 'Maj. Fictício Gestor', 0);
