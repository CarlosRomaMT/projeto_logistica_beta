import { useRef, useState } from 'react'
import { CargaLotacao } from './pages/CargaLotacao'
import { CorrecaoDivergencias } from './pages/CorrecaoDivergencias'
import { GradeCautela } from './pages/GradeCautela'
import { MovimentacaoViatura } from './pages/MovimentacaoViatura'
import { ValidacaoDePara } from './pages/ValidacaoDePara'
import { ViaturasSemOpm } from './pages/ViaturasSemOpm'

type Aba = 'operacao' | 'implantacao'

export default function App() {
  const [sinalRecarga, setSinalRecarga] = useState(0)
  const [aba, setAba] = useState<Aba>('operacao')
  const [revisor, setRevisor] = useState('')
  const campoRevisor = useRef<HTMLInputElement>(null)
  const recarregarTudo = () => setSinalRecarga((n) => n + 1)
  const semRevisor = !revisor.trim()

  // Chamado pelas etapas quando o usuário tenta agir sem se identificar: leva até o campo.
  function pedirRevisor() {
    campoRevisor.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    campoRevisor.current?.focus({ preventScroll: true })
  }

  return (
    <>
      <header className="topo">
        <div>
          <h1>Frota PMMT: lotação de viaturas</h1>
          <p>Primeira versão demonstrável · todos os dados são fictícios</p>
        </div>
        <button type="button" className="secundario" onClick={recarregarTudo}>
          Recarregar telas
        </button>
      </header>
      <nav className="abas" role="tablist">
        <button type="button" role="tab" aria-selected={aba === 'operacao'} onClick={() => setAba('operacao')}>
          Operação
        </button>
        <button type="button" role="tab" aria-selected={aba === 'implantacao'} onClick={() => setAba('implantacao')}>
          Implantação
        </button>
      </nav>

      {aba === 'operacao' ? (
        <main className="grade">
          <MovimentacaoViatura onMovimentada={recarregarTudo} sinalRecarga={sinalRecarga} />
          <GradeCautela sinalRecarga={sinalRecarga} />
        </main>
      ) : (
        <main className="implantacao">
          <section className={`painel revisor${semRevisor ? ' revisor-pendente' : ''}`}>
            <label>
              Revisor
              <input
                ref={campoRevisor}
                value={revisor}
                onChange={(e) => setRevisor(e.target.value)}
                placeholder="Seu usuário (ex.: sgt.revisor)"
                maxLength={60}
              />
            </label>
            {semRevisor && (
              <div role="status" className="aviso aviso-alerta">
                Informe seu usuário para liberar as ações das etapas abaixo (confirmar, executar, aplicar).
              </div>
            )}
            <small className="suave">
              Sem login no MVP: o nome informado fica registrado em cada decisão. Em produção vem do SSO e só perfis
              autorizados acessam esta aba.
            </small>
            <p className="etapas-intro">Migração do cadastro antigo de unidades para o novo, em quatro etapas, nesta ordem:</p>
            <ol className="etapas">
              <li>Associar as unidades antigas às OPMs: dizer a qual OPM corresponde cada unidade do cadastro antigo.</li>
              <li>Carga da lotação: lotar as viaturas nas OPMs associadas.</li>
              <li>Corrigir divergências: decidir sobre as viaturas em que o cadastro antigo e o novo discordam.</li>
              <li>Lotar as viaturas que ficaram sem OPM: escolher a OPM de cada uma que a carga deixou na OPM 0.</li>
            </ol>
          </section>
          <ValidacaoDePara revisor={revisor} pedirRevisor={pedirRevisor} sinalRecarga={sinalRecarga} onAlterado={recarregarTudo} />
          <CargaLotacao revisor={revisor} pedirRevisor={pedirRevisor} sinalRecarga={sinalRecarga} onAlterado={recarregarTudo} />
          <CorrecaoDivergencias revisor={revisor} pedirRevisor={pedirRevisor} sinalRecarga={sinalRecarga} onAlterado={recarregarTudo} />
          <ViaturasSemOpm revisor={revisor} pedirRevisor={pedirRevisor} sinalRecarga={sinalRecarga} onAlterado={recarregarTudo} />
        </main>
      )}
    </>
  )
}
