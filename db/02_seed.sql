-- Dados FICTÍCIOS que reproduzem o problema: viaturas lotadas só pela coluna antiga.

INSERT INTO tb_opm (id_opm, nome, status) VALUES
    (0, 'OPM 0 - Sem ligação (contingência)',             'ATIVA'),
    (1, '1º Batalhão de Polícia Militar - Centro',         'ATIVA'),
    (2, '2º Batalhão de Polícia Militar - Norte',          'ATIVA'),
    (3, '3º Batalhão de Polícia Militar - Sul',            'ATIVA'),
    (4, '1ª Companhia Independente de Polícia Militar',    'ATIVA'),
    (5, '5º Batalhão de Polícia Militar (extinto)',        'INATIVA'),
    (6, 'Batalhão de Polícia Militar de Trânsito',         'ATIVA');

-- Descrições do cadastro antigo: abreviadas e com grafias diferentes para a mesma unidade.
INSERT INTO tb_unidade_legado (cd_unidade, ds_unidade) VALUES
    ('101', '1º BPM - CENTRO'),               -- igual à OPM 1 após normalizar
    ('111', 'PRIMEIRO BATALHAO PM CENTRO'),   -- outra grafia da OPM 1
    ('102', '2 B.P.M. NORTE'),                -- igual à OPM 2 após normalizar
    ('103', '3º BTL PM'),                     -- parecida com a OPM 3 (falta "Sul"): pendente
    ('104', '1ª CIA IND PM'),                 -- igual à OPM 4 após normalizar
    ('105', '5º BPM (EXTINTO)'),              -- corresponde a uma OPM inativa
    ('106', 'BPTRAN');                        -- sigla sem correspondência automática

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
    -- Código inexistente no cadastro antigo: contingência.
    ('GHI1N11', 'Ford Ranger',       'DISPONIVEL', '999', NULL),
    ('GHI3P33', 'Toyota Hilux',      'CAUTELADA',  '000', NULL),
    -- Unidade antiga sem nenhuma OPM parecida: contingência.
    ('GHI2O22', 'Mitsubishi L200',   'DISPONIVEL', '106', NULL),
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
