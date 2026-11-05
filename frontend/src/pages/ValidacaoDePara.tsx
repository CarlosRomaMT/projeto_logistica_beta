import { useCallback, useEffect, useState } from 'react'
import { ErroApi, requisitar } from '../api/client'
import { AVISO_SEM_REVISOR, EtapaTitulo } from '../components/EtapaTitulo/EtapaTitulo'
import { SeletorOpm } from '../components/SeletorOpm/SeletorOpm'
import type {
  DeParaRevisao,
  Opm,
  ResultadoConfirmacao,
  ResultadoSugestaoIa,
  StatusIa,
} from '../types'

interface Props {
  revisor: string
  pedirRevisor: () => void
  sinalRecarga: number
  onAlterado: () => void
}

type Aviso = { tipo: 'sucesso' | 'erro'; texto: string }

const ROTULO = {
  PENDENTE: { classe: 'selo-manutencao', texto: 'Sugestão a confirmar' },
  IA: { classe: 'selo-ia', texto: 'Sugestão da IA' },
  SEM_CORRESPONDENCIA: { classe: 'selo-erro', texto: 'Sem sugestão: escolha a OPM' },
  OPM_INATIVA: { classe: 'selo-erro', texto: 'OPM inativa: escolha outra' },
  ALTERANDO: { classe: 'selo', texto: 'Alterando' },
}

/** Associada a uma OPM extinta: confirmada, mas as viaturas não têm para onde ir. */
const opmInativa = (d: DeParaRevisao) => d.situacao === 'CONFIRMADO' && d.status_opm !== 'ATIVA'

const pct = (x: number) => `${Math.round(x * 100)}%`

/** O que a IA disse sobre a unidade, para o revisor decidir (a IA nunca confirma sozinha). */
function OutrasOpcoes({ d, onEscolher }: { d: DeParaRevisao; onEscolher: (opm: Opm) => void }) {
  if (!d.ia_alternativas?.length) return null
  return (
    <div className="opcoes-ia">
      <span className="suave">Outras opções:</span>
      {d.ia_alternativas.map((o) => (
        <button
          key={o.id_opm}
          type="button"
          className="secundario"
          title="Preenche a OPM correta; confira e clique em Confirmar"
          onClick={() => onEscolher({ id_opm: o.id_opm, nome: o.nome, status: 'ATIVA' })}
        >
          {o.nome}
        </button>
      ))}
    </div>
  )
}

function ParecerIa({ d, onEscolher }: { d: DeParaRevisao; onEscolher: (opm: Opm) => void }) {
  if (d.situacao === 'CONFIRMADO' || !d.ia_resultado) return null
  if (d.metodo === 'IA') {
    return (
      <>
        <div className="suave">
          confiança {d.ia_confianca !== null ? pct(d.ia_confianca) : '—'} · {d.ia_modelo}
        </div>
        {d.ia_justificativa && <div className="suave justificativa-ia">“{d.ia_justificativa}”</div>}
        {d.ia_alerta && (
          <div className="alerta-ia" role="note">
            ⚠ {d.ia_alerta}
          </div>
        )}
        <OutrasOpcoes d={d} onEscolher={onEscolher} />
      </>
    )
  }
  const texto =
    d.ia_resultado === 'DESCARTADA'
      ? 'IA: resposta descartada pela validação'
      : `IA: nenhuma OPM corresponde com segurança${d.ia_nome_opm ? ` (talvez ${d.ia_nome_opm})` : ''}`
  return (
    <>
      <div className="suave">{texto}</div>
      {d.ia_resultado !== 'DESCARTADA' && d.ia_justificativa && (
        <div className="suave justificativa-ia">“{d.ia_justificativa}”</div>
      )}
      <OutrasOpcoes d={d} onEscolher={onEscolher} />
    </>
  )
}

function comoFoiConfirmada(d: DeParaRevisao) {
  if (d.metodo === 'EXATO') return 'Nome idêntico (automático)'
  const ia = d.ia_id_opm === null ? '' : d.ia_id_opm === d.id_opm ? ' · sugestão da IA aceita' : ' · IA sugeria outra'
  return `Manual: ${d.confirmado_por ?? '—'}${ia}`
}

function sugestaoComoOpm(d: DeParaRevisao): Opm | null {
  return d.id_opm !== null && d.nome_opm && !opmInativa(d) ? { id_opm: d.id_opm, nome: d.nome_opm, status: 'ATIVA' } : null
}

/** Etapa 1 (de-para): confirma ou altera a OPM de cada unidade antiga e lota na hora as viaturas dela. */
export function ValidacaoDePara({ revisor, pedirRevisor, sinalRecarga, onAlterado }: Props) {
  const [linhas, setLinhas] = useState<DeParaRevisao[]>([])
  const [escolhas, setEscolhas] = useState<Record<string, Opm | null>>({})
  const [editando, setEditando] = useState<Set<string>>(new Set())
  const [enviando, setEnviando] = useState<string | null>(null)
  const [aviso, setAviso] = useState<Aviso | null>(null)
  const [statusIa, setStatusIa] = useState<StatusIa | null>(null)
  const [sugerindo, setSugerindo] = useState(false)

  const carregar = useCallback(() => {
    requisitar<DeParaRevisao[]>('/logistica/api/de-para')
      .then((dados) => {
        setLinhas(dados)
        setEscolhas(Object.fromEntries(dados.map((d) => [d.cd_unidade_legado, sugestaoComoOpm(d)])))
      })
      .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
  }, [])

  useEffect(carregar, [carregar, sinalRecarga])

  const carregarStatusIa = useCallback(() => {
    requisitar<StatusIa>('/logistica/api/de-para/ia/status')
      .then(setStatusIa)
      .catch(() =>
        setStatusIa({ habilitada: true, disponivel: false, modelo: '', motivo: 'Não foi possível consultar a IA.' }),
      )
  }, [])

  useEffect(carregarStatusIa, [carregarStatusIa])

  async function sugerirComIa() {
    if (!revisor.trim()) {
      setAviso({ tipo: 'erro', texto: AVISO_SEM_REVISOR })
      pedirRevisor()
      return
    }
    setSugerindo(true)
    setAviso(null)
    try {
      const r = await requisitar<ResultadoSugestaoIa>('/logistica/api/de-para/ia/sugerir', {
        method: 'POST',
        body: JSON.stringify({ usuario: revisor.trim() }),
      })
      setAviso({ tipo: r.ia_disponivel ? 'sucesso' : 'erro', texto: r.mensagem })
      carregar()
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação com o servidor.' })
    } finally {
      setSugerindo(false)
      carregarStatusIa()
    }
  }

  // O pedido de revisor deixa de valer assim que o campo é preenchido.
  useEffect(() => {
    if (revisor.trim()) setAviso((a) => (a?.texto === AVISO_SEM_REVISOR ? null : a))
  }, [revisor])

  function alternarEdicao(cd: string, ligar: boolean) {
    setEditando((atual) => {
      const novo = new Set(atual)
      if (ligar) novo.add(cd)
      else novo.delete(cd)
      return novo
    })
  }

  async function confirmar(cd: string) {
    if (!revisor.trim()) {
      setAviso({ tipo: 'erro', texto: AVISO_SEM_REVISOR })
      pedirRevisor()
      return
    }
    const escolhida = escolhas[cd]
    if (!escolhida) {
      setAviso({ tipo: 'erro', texto: `Escolha a OPM correta da unidade ${cd} antes de confirmar.` })
      return
    }
    setEnviando(cd)
    setAviso(null)
    try {
      const r = await requisitar<ResultadoConfirmacao>(`/logistica/api/de-para/${cd}/confirmar`, {
        method: 'POST',
        body: JSON.stringify({ id_opm: escolhida.id_opm, usuario: revisor.trim() }),
      })
      const partes = [`Unidade ${cd} associada a ${r.de_para.nome_opm}.`]
      partes.push(r.movidas.length ? `Viaturas lotadas nela: ${r.movidas.join(', ')}.` : 'Nenhuma viatura precisou mudar.')
      if (r.bloqueadas.length) {
        partes.push(
          `Não puderam ser lotadas (${r.bloqueadas.map((b) => `${b.placa}: ${b.status.toLowerCase()}`).join(', ')}).`,
        )
      }
      setAviso({ tipo: 'sucesso', texto: partes.join(' ') })
      alternarEdicao(cd, false)
      onAlterado()
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação.' })
    } finally {
      setEnviando(null)
    }
  }

  const precisaDecisao = (d: DeParaRevisao) => d.situacao !== 'CONFIRMADO' || opmInativa(d)
  const pendentes = linhas.filter((d) => precisaDecisao(d) || editando.has(d.cd_unidade_legado))
  const confirmadas = linhas.filter((d) => !precisaDecisao(d) && !editando.has(d.cd_unidade_legado))
  const aguardandoDecisao = linhas.filter(precisaDecisao).length

  function rotulo(d: DeParaRevisao) {
    if (opmInativa(d)) return ROTULO.OPM_INATIVA
    if (d.situacao === 'CONFIRMADO') return ROTULO.ALTERANDO
    if (d.metodo === 'IA') return ROTULO.IA
    return ROTULO[d.situacao]
  }

  return (
    <section className="painel">
      <EtapaTitulo
        numero={1}
        titulo="Associar as unidades antigas às OPMs"
        situacao={linhas.length ? (aguardandoDecisao ? `${aguardandoDecisao} unidade(s) aguardando decisão` : 'Concluída') : null}
        pendente={aguardandoDecisao > 0}
      />
      <p className="nota">
        O cadastro antigo identifica a unidade só pelo nome, escrito de várias formas (ex.: "NPM RIO CLARO DO NORTE - 2º BPM"). O sistema
        sugere a OPM com o nome mais parecido e, em <strong>Sugerir com IA</strong>, um modelo de IA local (Qwen) analisa
        as unidades sem associação e explica a sugestão. Nenhuma sugestão é aplicada sozinha: confirme ou escolha outra. O que você confirma aqui é aplicado
        na hora às viaturas da unidade, com registro no histórico. As associações automáticas (nome idêntico) são
        aplicadas pela carga (etapa 2). Uma associação errada pode ser alterada em <strong>Alterar</strong>: as viaturas
        lotadas por ela e nunca movimentadas depois vão para a nova OPM.
      </p>
      <div className="faixa-ia">
        <button
          type="button"
          className="secundario"
          disabled={sugerindo || enviando !== null || aguardandoDecisao === 0 || statusIa?.habilitada === false}
          onClick={sugerirComIa}
          title="A IA só sugere: nada é gravado nas viaturas até você confirmar"
        >
          {sugerindo ? 'IA analisando…' : 'Sugerir com IA'}
        </button>
        <span className="suave">
          {statusIa === null
            ? 'Verificando a IA…'
            : statusIa.disponivel
              ? `IA local pronta (${statusIa.modelo}). Ela só sugere; a decisão é sua.`
              : `IA indisponível: ${statusIa.motivo} As sugestões por semelhança de nome continuam valendo.`}
        </span>
      </div>
      {aviso && (
        <div role="alert" className={`aviso aviso-${aviso.tipo}`}>
          {aviso.texto}
        </div>
      )}

      <h3>Aguardando decisão ({pendentes.length})</h3>
      {/* Sem área de rolagem: ela cortaria a lista de opções do SeletorOpm. */}
      <div>
        <table>
          <thead>
            <tr>
              <th>Unidade antiga</th>
              <th>Situação</th>
              <th title="Viaturas ativas desta unidade ainda sem OPM ou na OPM 0">Viaturas sem OPM</th>
              <th className="col-opm">OPM correta</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pendentes.map((d) => {
              const r = rotulo(d)
              const emEdicao = editando.has(d.cd_unidade_legado) && !precisaDecisao(d)
              return (
                <tr key={d.cd_unidade_legado}>
                  <td>
                    <span className="placa">{d.cd_unidade_legado}</span> {d.ds_unidade_legado}
                  </td>
                  <td>
                    <span className={`selo ${r.classe}`}>{r.texto}</span>
                    {d.situacao === 'PENDENTE' && d.metodo === 'SIMILARIDADE' && d.score !== null && (
                      <div className="suave">semelhança {pct(d.score)}</div>
                    )}
                    <ParecerIa
                      d={d}
                      onEscolher={(opm) => setEscolhas((e) => ({ ...e, [d.cd_unidade_legado]: opm }))}
                    />
                    {opmInativa(d) && <div className="suave">associada a {d.nome_opm}</div>}
                    {emEdicao && <div className="suave">hoje: {d.nome_opm}</div>}
                    {d.observacao && <div className="suave">{d.observacao}</div>}
                  </td>
                  <td>{d.qtd_viaturas_contingencia}</td>
                  <td className="col-opm">
                    <SeletorOpm
                      valor={escolhas[d.cd_unidade_legado] ?? null}
                      onChange={(opm) => setEscolhas((e) => ({ ...e, [d.cd_unidade_legado]: opm }))}
                    />
                  </td>
                  <td>
                    <div className="linha">
                      <button
                        type="button"
                        disabled={enviando !== null}
                        onClick={() => confirmar(d.cd_unidade_legado)}
                      >
                        {enviando === d.cd_unidade_legado ? 'Gravando…' : 'Confirmar'}
                      </button>
                      {emEdicao && (
                        <button type="button" className="secundario" onClick={() => alternarEdicao(d.cd_unidade_legado, false)}>
                          Cancelar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {pendentes.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">
                  {linhas.length ? 'Nenhuma unidade aguardando decisão.' : 'A lista de unidades antigas ainda não foi gerada. Ela é criada quando o sistema inicia: acione o suporte.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h3>Confirmadas ({confirmadas.length})</h3>
      <div className="rolagem">
        <table>
          <thead>
            <tr>
              <th>Unidade antiga</th>
              <th>OPM</th>
              <th>Como</th>
              <th title="Viaturas ativas desta unidade ainda sem OPM ou na OPM 0: a carga (etapa 2) as lota">
                Viaturas aguardando a carga
              </th>
              <th />
            </tr>
          </thead>
          <tbody>
            {confirmadas.map((d) => (
              <tr key={d.cd_unidade_legado}>
                <td>
                  <span className="placa">{d.cd_unidade_legado}</span> {d.ds_unidade_legado}
                </td>
                <td>{d.nome_opm}</td>
                <td className="suave">{comoFoiConfirmada(d)}</td>
                <td>{d.qtd_viaturas_contingencia || ''}</td>
                <td>
                  <button type="button" className="secundario" onClick={() => alternarEdicao(d.cd_unidade_legado, true)}>
                    Alterar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
