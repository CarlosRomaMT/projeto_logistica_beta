import { useCallback, useEffect, useState } from 'react'
import { ErroApi, requisitar } from '../api/client'
import { AVISO_SEM_REVISOR, EtapaTitulo } from '../components/EtapaTitulo/EtapaTitulo'
import type { PropostaCorrecao } from '../types'

interface Props {
  revisor: string
  pedirRevisor: () => void
  sinalRecarga: number
  onAlterado: () => void
}

type Aviso = { tipo: 'sucesso' | 'erro'; texto: string }

/** Correção das viaturas cuja coluna nova diverge do legado: nada é aplicado sem decisão humana. */
export function CorrecaoDivergencias({ revisor, pedirRevisor, sinalRecarga, onAlterado }: Props) {
  const [propostas, setPropostas] = useState<PropostaCorrecao[]>([])
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set())
  const [ocupado, setOcupado] = useState(false)
  const [aviso, setAviso] = useState<Aviso | null>(null)

  const carregar = useCallback(() => {
    requisitar<PropostaCorrecao[]>('/logistica/api/divergencias')
      .then((dados) => {
        setPropostas(dados)
        setSelecionadas(new Set())
      })
      .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
  }, [])

  useEffect(carregar, [carregar, sinalRecarga])

  useEffect(() => {
    if (revisor.trim()) setAviso((a) => (a?.texto === AVISO_SEM_REVISOR ? null : a))
  }, [revisor])

  async function executar(acao: () => Promise<string>) {
    setOcupado(true)
    setAviso(null)
    try {
      setAviso({ tipo: 'sucesso', texto: await acao() })
      carregar()
      onAlterado()
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação.' })
    } finally {
      setOcupado(false)
    }
  }

  const procurar = () =>
    executar(async () => {
      const r = await requisitar<{ criadas: number }>('/logistica/api/divergencias/procurar', { method: 'POST' })
      return r.criadas ? `${r.criadas} nova(s) proposta(s) de correção.` : 'Nenhuma divergência nova.'
    })

  function decidir(acao: 'aplicar' | 'rejeitar') {
    if (!revisor.trim()) {
      setAviso({ tipo: 'erro', texto: AVISO_SEM_REVISOR })
      pedirRevisor()
      return
    }
    executar(async () => {
      const corpo = JSON.stringify({ ids: [...selecionadas], usuario: revisor.trim() })
      if (acao === 'aplicar') {
        const r = await requisitar<{ aplicadas: string[] }>('/logistica/api/divergencias/aplicar', { method: 'POST', body: corpo })
        return `Corrigidas: ${r.aplicadas.join(', ')}.`
      }
      const r = await requisitar<{ rejeitadas: number }>('/logistica/api/divergencias/rejeitar', { method: 'POST', body: corpo })
      return `${r.rejeitadas} proposta(s) rejeitada(s). Essas viaturas ficam como estão.`
    })
  }

  function alternar(id: number) {
    setSelecionadas((atual) => {
      const nova = new Set(atual)
      if (nova.has(id)) nova.delete(id)
      else nova.add(id)
      return nova
    })
  }

  const abertas = propostas.filter((p) => p.situacao === 'PROPOSTA')
  const decididas = propostas.filter((p) => p.situacao !== 'PROPOSTA')

  return (
    <section className="painel">
      <EtapaTitulo
        numero={3}
        titulo="Corrigir divergências"
        situacao={abertas.length ? `${abertas.length} proposta(s) em aberto` : 'Nenhuma proposta em aberto'}
        pendente={abertas.length > 0}
      />
      <p className="nota">
        Viaturas cuja coluna nova aponta para uma OPM e o cadastro antigo para outra (o problema original). As propostas
        são geradas pela carga (etapa 2) ou pelo botão Procurar divergências. Só entram
        viaturas nunca movimentadas pelo sistema novo. A correção usa a movimentação normal e fica no histórico; na
        implantação, viatura cautelada também pode ser corrigida.
      </p>
      <div className="linha">
        <button type="button" className="secundario" onClick={procurar} disabled={ocupado}>
          Procurar divergências
        </button>
        <button type="button" onClick={() => decidir('aplicar')} disabled={ocupado || !selecionadas.size}>
          Aplicar selecionadas
        </button>
        <button type="button" className="secundario" onClick={() => decidir('rejeitar')} disabled={ocupado || !selecionadas.size}>
          Rejeitar selecionadas
        </button>
      </div>
      {/* A dica fica sempre no mesmo lugar: se sumisse ao marcar, os botões mudariam de posição. */}
      {abertas.length > 0 && (
        <small className="suave">
          {selecionadas.size
            ? `${selecionadas.size} proposta(s) selecionada(s).`
            : 'Marque na lista abaixo as propostas que deseja aplicar ou rejeitar.'}
        </small>
      )}
      {aviso && (
        <div role="alert" className={`aviso aviso-${aviso.tipo}`}>
          {aviso.texto}
        </div>
      )}

      <h3>Aguardando decisão ({abertas.length})</h3>
      <div className="rolagem">
        <table>
          <thead>
            <tr>
              <th />
              <th>Placa</th>
              <th>Unidade antiga</th>
              <th>OPM atual</th>
              <th>OPM proposta</th>
            </tr>
          </thead>
          <tbody>
            {abertas.map((p) => (
              <tr key={p.id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Selecionar ${p.placa}`}
                    disabled={p.bloqueio !== null}
                    checked={selecionadas.has(p.id)}
                    onChange={() => alternar(p.id)}
                  />
                </td>
                <td className="placa">
                  {p.placa}
                  {p.bloqueio && <div><span className="selo selo-cautelada">Bloqueada: {p.bloqueio}</span></div>}
                </td>
                <td>
                  <span className="placa">{p.cd_unidade_legado}</span> {p.ds_unidade_legado}
                </td>
                <td>{p.nome_opm_atual}</td>
                <td>
                  <strong>{p.nome_opm_proposta}</strong>
                </td>
              </tr>
            ))}
            {abertas.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">
                  Nenhuma proposta em aberto.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {decididas.length > 0 && (
        <>
          <h3>Decididas ({decididas.length})</h3>
          <div className="rolagem">
            <table>
              <thead>
                <tr>
                  <th>Placa</th>
                  <th>Decisão</th>
                  <th>De → para</th>
                  <th>Por</th>
                </tr>
              </thead>
              <tbody>
                {decididas.map((p) => (
                  <tr key={p.id}>
                    <td className="placa">{p.placa}</td>
                    <td>
                      <span className={`selo ${p.situacao === 'APLICADA' ? 'selo-disponivel' : 'selo-erro'}`}>
                        {p.situacao === 'APLICADA' ? 'Corrigida' : 'Rejeitada'}
                      </span>
                    </td>
                    <td className="suave">
                      {p.nome_opm_atual} → {p.nome_opm_proposta}
                    </td>
                    <td className="suave">{p.decidido_por}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
