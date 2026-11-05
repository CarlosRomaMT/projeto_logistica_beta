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

-- Unidades JÁ PARCIALMENTE MIGRADAS: as viaturas delas têm as duas colunas preenchidas, como os 6.656
-- veículos assim no banco de desenvolvimento. Esse histórico é a ponte mais forte entre os cadastros
-- (camada "histórico" do de-para) e alimenta o RAG de exemplos. Padrões reais, nomes inventados.
INSERT INTO tb_opm (id_opm, nome, abreviatura, status) VALUES
    (12, 'NUCLEO PM - AGUA CLARA DO SUL', 'NPM - AGUA CLARA DO SUL', 'ATIVA'),
    (13, 'NUCLEO PM - VALE DO SOL', 'NPM - VALE DO SOL', 'ATIVA'),
    (14, 'NUCLEO PM - MORRO AZUL', 'NPM - MORRO AZUL', 'ATIVA'),
    (15, 'NUCLEO PM - PONTE ALTA DO NORTE', 'NPM - PONTE ALTA DO NORTE', 'ATIVA'),
    (16, 'NUCLEO PM - SAO BENTO DA SERRA', 'NPM - SAO BENTO DA SERRA', 'ATIVA'),
    (17, 'NUCLEO PM - PALMEIRAL', 'NPM - PALMEIRAL', 'ATIVA'),
    (18, '1º PELOTAO PM - CACHOEIRA FRIA', '1º PEL PM - 3º BPM', 'ATIVA'),
    (19, '2º PELOTAO PM - NOVA ESMERALDA', '2º PEL PM - 4º BPM', 'ATIVA'),
    (20, '1º PELOTAO PM - PORTO SOLAR', '1º PEL PM - 6º BPM', 'ATIVA'),
    (21, '3º PELOTAO PM - RIACHO FUNDO', '3º PEL PM - 6º BPM', 'ATIVA'),
    (22, '2º PELOTAO PM - BARRA FUNDA', '2º PEL PM - 4º BPM', 'ATIVA'),
    (23, '1º PELOTAO PM - SANTA LUZIA DO LESTE', '1º PEL PM - 7º BPM', 'ATIVA'),
    (24, '1ª CIA PM - 3º BPM', '1ª CIA PM - 3º BPM', 'ATIVA'),
    (25, '2ª CIA PM - 4º BPM', '2ª CIA PM - 4º BPM', 'ATIVA'),
    (26, '3ª CIA PM - 6º BPM', '3ª CIA PM - 6º BPM', 'ATIVA'),
    (27, '1ª CIA PM - 7º BPM', '1ª CIA PM - 7º BPM', 'ATIVA'),
    (28, '3º COMANDO REGIONAL', '3º CR', 'ATIVA'),
    (29, '7º COMANDO REGIONAL', '7º CR', 'ATIVA'),
    (30, '4º BATALHAO DE POLICIA MILITAR', '4º BPM - 3º CR', 'ATIVA'),
    (31, '6º BATALHAO DE POLICIA MILITAR', '6º BPM - 7º CR', 'ATIVA'),
    (32, 'BATALHAO DE POLICIA MILITAR AMBIENTAL', 'BPMAMB - CESP', 'ATIVA'),
    (33, 'BATALHAO ROTAM', 'BROTAM - CESP', 'ATIVA'),
    (34, 'BATALHAO DE OPERACOES POLICIAIS ESPECIAIS', 'BOPE - CESP', 'ATIVA'),
    (35, 'BATALHAO DE POLICIA MILITAR DE GUARDA', 'BPGUARDA - CESP', 'ATIVA');

INSERT INTO tb_unidade_legado (cd_unidade, ds_unidade) VALUES
    ('201', 'NPM AGUA CLARA DO SUL - 3º BPM'),
    ('202', 'NPM VALE DO SOL - 3º BPM'),
    ('203', 'NPM MORRO AZUL - 4º BPM'),
    ('204', 'NPM PONTE ALTA DO NORTE - 6º BPM'),
    ('205', 'NPM SAO BENTO DA SERRA - 4ª CIPM'),
    ('206', 'NPM PALMEIRAL - 7º BPM'),
    ('207', 'NPM CACHOEIRA FRIA'),
    ('208', 'NPM NOVA ESMERALDA'),
    ('209', 'NPM PORTO SOLAR'),
    ('210', '3º PEL PM RIACHO FUNDO - 6º BPM'),
    ('211', '2º PEL PM BARRA FUNDA - 4º BPM'),
    ('212', '1º PEL PM SANTA LUZIA DO LESTE - 7º BPM'),
    ('213', '1ª CIA PM AGUA CLARA DO SUL - 3º BPM'),
    ('214', '2ª CIA PM MORRO AZUL - 4º BPM'),
    ('215', '3ª CIA PM VALE DO SOL - 6º BPM'),
    ('216', '1ª CIA PM PALMEIRAL - 7º BPM'),
    ('217', 'CR 3 - SEDE'),
    ('218', 'CR 7 - SEDE'),
    ('219', '4º BPM - MORRO AZUL'),
    ('220', '6º BPM - PONTE ALTA DO NORTE'),
    ('221', 'BPMA'),
    ('222', 'ROTAM'),
    ('223', 'BOPE - SEDE'),
    ('224', 'CIA IND GUARDA');

INSERT INTO tb_viatura (placa, modelo, status_operacional, cd_unidade_legado, fk_id_opm_unidade) VALUES
    ('HST0101', 'Chevrolet S10', 'DISPONIVEL', '201', 12),
    ('HST0102', 'Renault Duster', 'DISPONIVEL', '201', 12),
    ('HST0201', 'Ford Ranger', 'DISPONIVEL', '202', 13),
    ('HST0202', 'Mitsubishi L200', 'DISPONIVEL', '202', 13),
    ('HST0301', 'Chevrolet Spin', 'DISPONIVEL', '203', 14),
    ('HST0302', 'Toyota Hilux', 'DISPONIVEL', '203', 14),
    ('HST0401', 'Chevrolet S10', 'DISPONIVEL', '204', 15),
    ('HST0402', 'Renault Duster', 'DISPONIVEL', '204', 15),
    ('HST0501', 'Ford Ranger', 'DISPONIVEL', '205', 16),
    ('HST0502', 'Mitsubishi L200', 'DISPONIVEL', '205', 16),
    ('HST0601', 'Chevrolet Spin', 'DISPONIVEL', '206', 17),
    ('HST0602', 'Toyota Hilux', 'DISPONIVEL', '206', 17),
    ('HST0701', 'Chevrolet S10', 'DISPONIVEL', '207', 18),
    ('HST0702', 'Renault Duster', 'DISPONIVEL', '207', 18),
    ('HST0801', 'Ford Ranger', 'DISPONIVEL', '208', 19),
    ('HST0802', 'Mitsubishi L200', 'DISPONIVEL', '208', 19),
    ('HST0901', 'Chevrolet Spin', 'DISPONIVEL', '209', 20),
    ('HST0902', 'Toyota Hilux', 'DISPONIVEL', '209', 20),
    ('HST1001', 'Chevrolet S10', 'DISPONIVEL', '210', 21),
    ('HST1002', 'Renault Duster', 'DISPONIVEL', '210', 21),
    ('HST1101', 'Ford Ranger', 'DISPONIVEL', '211', 22),
    ('HST1102', 'Mitsubishi L200', 'DISPONIVEL', '211', 22),
    ('HST1201', 'Chevrolet Spin', 'DISPONIVEL', '212', 23),
    ('HST1202', 'Toyota Hilux', 'DISPONIVEL', '212', 23),
    ('HST1301', 'Chevrolet S10', 'DISPONIVEL', '213', 24),
    ('HST1302', 'Renault Duster', 'DISPONIVEL', '213', 24),
    ('HST1401', 'Ford Ranger', 'DISPONIVEL', '214', 25),
    ('HST1402', 'Mitsubishi L200', 'DISPONIVEL', '214', 25),
    ('HST1501', 'Chevrolet Spin', 'DISPONIVEL', '215', 26),
    ('HST1502', 'Toyota Hilux', 'DISPONIVEL', '215', 26),
    ('HST1601', 'Chevrolet S10', 'DISPONIVEL', '216', 27),
    ('HST1602', 'Renault Duster', 'DISPONIVEL', '216', 27),
    ('HST1701', 'Ford Ranger', 'DISPONIVEL', '217', 28),
    ('HST1702', 'Mitsubishi L200', 'DISPONIVEL', '217', 28),
    ('HST1801', 'Chevrolet Spin', 'DISPONIVEL', '218', 29),
    ('HST1802', 'Toyota Hilux', 'DISPONIVEL', '218', 29),
    ('HST1901', 'Chevrolet S10', 'DISPONIVEL', '219', 30),
    ('HST1902', 'Renault Duster', 'DISPONIVEL', '219', 30),
    ('HST2001', 'Ford Ranger', 'DISPONIVEL', '220', 31),
    ('HST2002', 'Mitsubishi L200', 'DISPONIVEL', '220', 31),
    ('HST2101', 'Chevrolet Spin', 'DISPONIVEL', '221', 32),
    ('HST2102', 'Toyota Hilux', 'DISPONIVEL', '221', 32),
    ('HST2201', 'Chevrolet S10', 'DISPONIVEL', '222', 33),
    ('HST2202', 'Renault Duster', 'DISPONIVEL', '222', 33),
    ('HST2301', 'Ford Ranger', 'DISPONIVEL', '223', 34),
    ('HST2302', 'Mitsubishi L200', 'DISPONIVEL', '223', 34),
    ('HST2401', 'Chevrolet Spin', 'DISPONIVEL', '224', 35),
    ('HST2402', 'Toyota Hilux', 'DISPONIVEL', '224', 35);

INSERT INTO tb_usuario_p4 (login, nome, fk_id_opm) VALUES
    ('p4.opm1',         'Cap. Fictício Um',     1),
    ('p4.opm2',         'Cap. Fictício Dois',   2),
    ('p4.opm3',         'Cap. Fictício Três',   3),
    ('p4.opm4',         'Ten. Fictício Quatro', 4),
    ('p4.contingencia', 'Maj. Fictício Gestor', 0);
