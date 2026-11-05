-- Schema compartilhado entre Logística e Cautela (dados e nomes fictícios).
-- Premissa do MVP: os dois sistemas usam o mesmo PostgreSQL (visibilidade imediata, RNF02).

DROP TABLE IF EXISTS tb_execucao_ia, tb_correcao_divergencia, tb_notificacao_pendente, tb_historico_movimentacao,
    tb_usuario_p4, tb_viatura, tb_de_para_unidade, tb_unidade_legado, tb_opm CASCADE;

-- Cadastro corporativo de OPMs (padrão novo).
-- Espelha sgpm.opm: nome em maiúsculas e sem acento, abreviatura própria (opm_abreviatura).
CREATE TABLE tb_opm (
    id_opm      INTEGER PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    abreviatura VARCHAR(40),
    status      VARCHAR(10)  NOT NULL CHECK (status IN ('ATIVA', 'INATIVA'))
);

-- Cadastro antigo de unidades, referenciado por tb_viatura.cd_unidade_legado.
-- Não há chave comum com tb_opm: só a descrição, que tem abreviações e grafias diferentes.
CREATE TABLE tb_unidade_legado (
    cd_unidade VARCHAR(10)  PRIMARY KEY,
    ds_unidade VARCHAR(120) NOT NULL
);

-- De-para unidade antiga -> OPM (RF04). Só linhas CONFIRMADO são usadas na carga.
-- Em PENDENTE, fk_id_opm guarda a sugestão que aguarda validação humana.
CREATE TABLE tb_de_para_unidade (
    cd_unidade_legado VARCHAR(10)  PRIMARY KEY,
    ds_unidade_legado VARCHAR(120) NOT NULL,
    fk_id_opm         INTEGER      REFERENCES tb_opm (id_opm),
    situacao          VARCHAR(20)  NOT NULL
        CHECK (situacao IN ('CONFIRMADO', 'PENDENTE', 'SEM_CORRESPONDENCIA')),
    metodo            VARCHAR(15)  CHECK (metodo IN ('EXATO', 'HISTORICO', 'SIMILARIDADE', 'IA', 'MANUAL')),
    score             NUMERIC(4, 3),
    observacao        VARCHAR(200),
    confirmado_por    VARCHAR(60),
    dt_confirmacao    TIMESTAMPTZ,
    dt_atualizacao    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    -- Última análise da IA (Qwen local). Só sugestão: quem decide é o revisor.
    ia_resultado      VARCHAR(20)  CHECK (ia_resultado IN ('ACEITA', 'SEM_CORRESPONDENCIA', 'BAIXA_CONFIANCA', 'DESCARTADA')),
    ia_id_opm         INTEGER      REFERENCES tb_opm (id_opm),
    ia_confianca      NUMERIC(4, 3),
    ia_justificativa  VARCHAR(200),
    ia_modelo         VARCHAR(60),
    dt_ia             TIMESTAMPTZ
);

-- Registro de cada chamada à IA (observabilidade): inclusive falhas e respostas descartadas.
CREATE TABLE tb_execucao_ia (
    id                SERIAL PRIMARY KEY,
    cd_unidade_legado VARCHAR(10)  NOT NULL,
    modelo            VARCHAR(60)  NOT NULL,
    resultado         VARCHAR(20)  NOT NULL,
    motivo            VARCHAR(40),
    id_opm            INTEGER,
    confianca         NUMERIC(4, 3),
    latencia_ms       INTEGER      NOT NULL,
    usuario           VARCHAR(60)  NOT NULL,
    dt_execucao       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE tb_viatura (
    id_viatura         SERIAL PRIMARY KEY,
    placa              VARCHAR(8)  NOT NULL UNIQUE,
    modelo             VARCHAR(60) NOT NULL,
    status_operacional VARCHAR(12) NOT NULL
        CHECK (status_operacional IN ('DISPONIVEL', 'CAUTELADA', 'MANUTENCAO', 'BAIXADA')),
    -- Coluna antiga: mantida no banco, mas nenhum fluxo grava nela (RF01).
    cd_unidade_legado  VARCHAR(10),
    -- Coluna padrão: única fonte de lotação (RF01, RF02).
    fk_id_opm_unidade  INTEGER REFERENCES tb_opm (id_opm),
    dt_atualizacao     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_viatura_opm_status ON tb_viatura (fk_id_opm_unidade, status_operacional);

CREATE TABLE tb_historico_movimentacao (
    id              SERIAL PRIMARY KEY,
    id_viatura      INTEGER     NOT NULL REFERENCES tb_viatura (id_viatura),
    id_opm_origem   INTEGER     REFERENCES tb_opm (id_opm),
    id_opm_destino  INTEGER     NOT NULL REFERENCES tb_opm (id_opm),
    tipo            VARCHAR(20) NOT NULL,
    usuario         VARCHAR(60) NOT NULL,
    dt_movimentacao TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tb_notificacao_pendente (
    id             SERIAL PRIMARY KEY,
    id_viatura     INTEGER     NOT NULL REFERENCES tb_viatura (id_viatura),
    id_opm_destino INTEGER     NOT NULL REFERENCES tb_opm (id_opm),
    mensagem       TEXT        NOT NULL,
    dt_criacao     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Propostas de correção para viaturas cuja coluna nova diverge do legado (o bug original).
-- Nada é aplicado sem decisão humana; a aplicação passa pelo serviço de movimentação.
CREATE TABLE tb_correcao_divergencia (
    id              SERIAL PRIMARY KEY,
    id_viatura      INTEGER     NOT NULL REFERENCES tb_viatura (id_viatura),
    id_opm_atual    INTEGER     NOT NULL REFERENCES tb_opm (id_opm),
    id_opm_proposta INTEGER     NOT NULL REFERENCES tb_opm (id_opm),
    situacao        VARCHAR(10) NOT NULL DEFAULT 'PROPOSTA'
        CHECK (situacao IN ('PROPOSTA', 'APLICADA', 'REJEITADA')),
    decidido_por    VARCHAR(60),
    dt_decisao      TIMESTAMPTZ,
    dt_criacao      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No máximo uma proposta em aberto por viatura.
CREATE UNIQUE INDEX ux_correcao_aberta ON tb_correcao_divergencia (id_viatura) WHERE situacao = 'PROPOSTA';

-- Tabela do Cautela: P4 (gestor de frota) e a OPM a que pertence.
CREATE TABLE tb_usuario_p4 (
    login     VARCHAR(40)  PRIMARY KEY,
    nome      VARCHAR(120) NOT NULL,
    fk_id_opm INTEGER      NOT NULL REFERENCES tb_opm (id_opm)
);
