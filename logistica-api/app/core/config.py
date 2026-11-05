STATUS_OPM_ATIVA = "ATIVA"

# OPM sintética que recebe as viaturas sem lotação resolvida (RF04).
ID_OPM_CONTINGENCIA = 0

STATUS_BAIXADA = "BAIXADA"
STATUS_CAUTELADA = "CAUTELADA"

# Status de viatura que bloqueiam movimentação (RF03).
# Pendente de validação com o dono da Logística.
STATUS_QUE_IMPEDEM_MOVIMENTACAO = {STATUS_BAIXADA, STATUS_CAUTELADA}

# Na implantação (associação da unidade antiga, carga, correção de divergências e lotação da OPM 0)
# a viatura cautelada pode mudar de lotação: decisão da gestão de frota em 2026-10-28.
STATUS_QUE_IMPEDEM_NA_IMPLANTACAO = {STATUS_BAIXADA}
