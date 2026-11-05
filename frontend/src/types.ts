export interface Opm {
  id_opm: number
  nome: string
  status: string
}

// A coluna legada não existe no frontend (RNF02).
export interface Viatura {
  id_viatura: number
  placa: string
  modelo: string
  status_operacional: string
  id_opm: number | null
  nome_opm: string | null
}

// Só para a visão de diagnóstico (demonstração do problema).
export interface LegadoViatura {
  id_viatura: number
  cd_unidade_legado: string | null
  ds_unidade_legado: string | null
  situacao_de_para: 'CONFIRMADO' | 'PENDENTE' | 'SEM_CORRESPONDENCIA' | null
  id_opm_de_para: number | null
  nome_opm_de_para: string | null
  score: number | null
}

// Implantação, etapa 1: validação do de-para (Melhoria 2).
export interface DeParaRevisao {
  cd_unidade_legado: string
  ds_unidade_legado: string
  situacao: 'CONFIRMADO' | 'PENDENTE' | 'SEM_CORRESPONDENCIA'
  metodo: string | null
  score: number | null
  id_opm: number | null
  nome_opm: string | null
  observacao: string | null
  confirmado_por: string | null
  dt_confirmacao: string | null
  status_opm: 'ATIVA' | 'INATIVA' | null
  qtd_viaturas_contingencia: number
  // Último parecer da IA (Qwen local): só sugestão, a decisão é do revisor.
  ia_resultado: 'ACEITA' | 'SEM_CORRESPONDENCIA' | 'BAIXA_CONFIANCA' | 'DESCARTADA' | null
  ia_id_opm: number | null
  ia_nome_opm: string | null
  ia_confianca: number | null
  ia_justificativa: string | null
  ia_modelo: string | null
  ia_alerta: string | null
  // Outras opções quando há dúvida (sem sugestão ou com alerta), na ordem do seletor.
  ia_alternativas: { id_opm: number; nome: string }[] | null
}

export interface StatusIa {
  habilitada: boolean
  disponivel: boolean
  modelo: string
  motivo: string | null
}

export interface ResultadoSugestaoIa {
  modelo: string
  analisadas: number
  sugestoes_novas: number
  sem_correspondencia: number
  descartadas: number
  falhas: number
  ia_disponivel: boolean
  mensagem: string
}

export interface ResultadoConfirmacao {
  de_para: DeParaRevisao
  movidas: string[]
  bloqueadas: { placa: string; status: string }[]
}

// Implantação, etapa 3: correção das divergências (Melhoria 1).
export interface PropostaCorrecao {
  id: number
  placa: string
  modelo: string
  status_operacional: string
  cd_unidade_legado: string | null
  ds_unidade_legado: string | null
  nome_opm_atual: string
  nome_opm_proposta: string
  situacao: 'PROPOSTA' | 'APLICADA' | 'REJEITADA'
  bloqueio: string | null
  decidido_por: string | null
  dt_decisao: string | null
}

export interface P4 {
  login: string
  nome: string
  id_opm: number
  nome_opm: string
}

export interface FrotaDisponivel {
  p4: P4
  viaturas: Pick<Viatura, 'id_viatura' | 'placa' | 'modelo'>[]
}

// Implantação, etapa 2: carga da lotação pela tela (RF04).
export interface Inconformidade {
  placa: string
  cd_unidade_legado: string | null
  ds_unidade_legado: string | null
  motivo: string
  opm_sugerida: string | null
  acao: string
}

export interface Lotada {
  placa: string
  cd_unidade_legado: string
  ds_unidade_legado: string
  nome_opm: string
}

export interface ResultadoCarga {
  simulacao: boolean
  atualizadas: number
  contingencia: number
  de_para_criados: number
  propostas_criadas: number
  lotadas: Lotada[]
  inconformidades: Inconformidade[]
  relatorio: string | null
}

// Implantação, etapa 4: viaturas que ficaram na OPM 0.
export interface ViaturaSemOpm {
  id_viatura: number
  placa: string
  modelo: string
  status_operacional: string
  cd_unidade_legado: string | null
  ds_unidade_legado: string | null
  motivo: string | null
  id_opm_sugerida: number | null
  nome_opm_sugerida: string | null
}
