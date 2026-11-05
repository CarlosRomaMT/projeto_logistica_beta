import { useCallback, useEffect, useState } from 'react'
import { ErroApi, requisitar } from '../api/client'
import { AVISO_SEM_REVISOR, EtapaTitulo } from '../components/EtapaTitulo/EtapaTitulo'
import { SeletorOpm } from '../components/SeletorOpm/SeletorOpm'
import type { Opm, Viatura, ViaturaSemOpm } from '../types'
import { MOTIVO } from './CargaLotacao'

interface Props {
  revisor: string
  pedirRevisor: () => void
  sinalRecarga: number
  onAlterado: () => void
}

type Aviso = { tipo: 'sucesso' | 'erro'; texto: string }

function sugestaoComoOpm(v: ViaturaSemOpm): Opm | null {
  return v.id_opm_sugerida !== null && v.nome_opm_sugerida
    ? { id_opm: v.id_opm_sugerida, nome: v.nome_opm_sugerida, status: 'ATIVA' }
    : null
}

/** Etapa 4: o que a carga deixou na OPM 0 é lotado viatura por viatura, pela movimentação normal. */
export function ViaturasSemOpm({ revisor, pedirRevisor, sinalRecarga, onAlterado }: Props) {
  const [viaturas, setViaturas] = useState<ViaturaSemOpm[]>([])
  const [escolhas, setEscolhas] = useState<Record<number, Opm | null>>({})
  const [enviando, setEnviando] = useState<number | null>(null)
  const [aviso, setAviso] = useState<Aviso | null>(null)

  const carregar = useCallback(() => {
    requisitar<ViaturaSemOpm[]>('/logistica/api/carga/sem-opm')
      .then((dados) => {
        setViaturas(dados)
        setEscolhas(Object.fromEntries(dados.map((v) => [v.id_viatura, sugestaoComoOpm(v)])))
      })
      .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
  }, [])

  useEffect(carregar, [carregar, sinalRecarga])

  useEffect(() => {
    if (revisor.trim()) setAviso((a) => (a?.texto === AVISO_SEM_REVISOR ? null : a))
  }, [revisor])

  async function lotar(v: ViaturaSemOpm) {
    if (!revisor.trim()) {
      setAviso({ tipo: 'erro', texto: AVISO_SEM_REVISOR })
      pedirRevisor()
      return
    }
    const escolhida = escolhas[v.id_viatura]
    if (!escolhida) {
      setAviso({ tipo: 'erro', texto: `Escolha a OPM da viatura ${v.placa} antes de lotar.` })
      return
    }
    setEnviando(v.id_viatura)
    setAviso(null)
    try {
      const r = await requisitar<Viatura>(`/logistica/api/carga/sem-opm/${v.id_viatura}/lotar`, {
        method: 'POST',
        body: JSON.stringify({ id_opm: escolhida.id_opm, usuario: revisor.trim() }),
      })
      setAviso({ tipo: 'sucesso', texto: `Viatura ${r.placa} lotada em ${r.nome_opm}.` })
      onAlterado()
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação.' })
    } finally {
      setEnviando(null)
    }
  }

  return (
    <section className="painel">
      <EtapaTitulo
        numero={4}
        titulo="Lotar as viaturas que ficaram sem OPM"
        situacao={viaturas.length ? `${viaturas.length} viatura(s) na OPM 0` : 'Nenhuma viatura na OPM 0'}
        pendente={viaturas.length > 0}
      />
      <p className="nota">
        Viaturas que a carga (etapa 2) não conseguiu lotar e deixou na OPM 0 (contingência), onde só o P4 da
        contingência as vê. Escolha a OPM de cada uma e clique em Lotar: a mudança fica no histórico. Se o problema for a
        unidade antiga (associação pendente ou com OPM inativa), resolver na etapa 1 lota todas as viaturas dela de uma
        vez. Na implantação, viatura cautelada também pode ser lotada.
      </p>
      {aviso && (
        <div role="alert" className={`aviso aviso-${aviso.tipo}`}>
          {aviso.texto}
        </div>
      )}

      {/* Sem área de rolagem: ela cortaria a lista de opções do SeletorOpm. */}
      <div>
        <table>
          <thead>
            <tr>
              <th>Placa</th>
              <th>Unidade antiga</th>
              <th>Motivo</th>
              <th className="col-opm">OPM</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {viaturas.map((v) => {
              const cautelada = v.status_operacional === 'CAUTELADA'
              return (
                <tr key={v.id_viatura}>
                  <td>
                    <span className="placa">{v.placa}</span>
                    <div className="suave">{v.modelo}</div>
                    {cautelada && <span className="selo selo-cautelada">Cautelada: em uso</span>}
                  </td>
                  <td>
                    <span className="placa">{v.cd_unidade_legado?.trim() || '—'}</span> {v.ds_unidade_legado}
                  </td>
                  <td>{v.motivo ? MOTIVO[v.motivo] ?? v.motivo : 'Unidade antiga já associada'}</td>
                  <td className="col-opm">
                    <SeletorOpm
                      valor={escolhas[v.id_viatura] ?? null}
                      onChange={(opm) => setEscolhas((e) => ({ ...e, [v.id_viatura]: opm }))}
                    />
                  </td>
                  <td>
                    <button type="button" disabled={enviando !== null} onClick={() => lotar(v)}>
                      {enviando === v.id_viatura ? 'Gravando…' : 'Lotar'}
                    </button>
                  </td>
                </tr>
              )
            })}
            {viaturas.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">
                  Nenhuma viatura na OPM 0.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
