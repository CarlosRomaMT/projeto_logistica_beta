export const TOTAL_ETAPAS = 4

export const AVISO_SEM_REVISOR = 'Informe seu usuário no campo Revisor, no topo da página, para continuar.'

interface Props {
  numero: number
  titulo: string
  /** Resumo do que falta nesta etapa; null enquanto carrega. */
  situacao: string | null
  pendente: boolean
}

/** Cabeçalho dos painéis da aba Implantação: deixa claro que são etapas de um mesmo processo, em ordem. */
export function EtapaTitulo({ numero, titulo, situacao, pendente }: Props) {
  return (
    <header className="painel-titulo">
      <span className="sistema">
        Etapa {numero} de {TOTAL_ETAPAS} · Logística
      </span>
      <h2>
        {titulo}
        {situacao && <span className={`selo selo-etapa ${pendente ? 'selo-manutencao' : 'selo-disponivel'}`}>{situacao}</span>}
      </h2>
    </header>
  )
}
