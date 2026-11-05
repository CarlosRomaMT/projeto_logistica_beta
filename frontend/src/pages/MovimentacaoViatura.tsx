import { useCallback, useEffect, useState } from 'react'
import { ErroApi, requisitar } from '../api/client'
import { SeletorOpm } from '../components/SeletorOpm/SeletorOpm'
import type { LegadoViatura, Opm, Viatura } from '../types'

interface Props {
  onMovimentada: () => void
  sinalRecarga: number
}

type Aviso = { tipo: 'sucesso' | 'erro'; texto: string }

/** Tela do Sistema de Logística: lista a frota e movimenta viaturas entre OPMs. */
export function MovimentacaoViatura({ onMovimentada, sinalRecarga }: Props) {
  const [viaturas, setViaturas] = useState<Viatura[]>([])
  const [idViatura, setIdViatura] = useState<number | ''>('')
  const [opm, setOpm] = useState<Opm | null>(null)
  const [incluirInativas, setIncluirInativas] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [aviso, setAviso] = useState<Aviso | null>(null)
  const [mostrarLegado, setMostrarLegado] = useState(false)
  const [legado, setLegado] = useState<Record<number, LegadoViatura>>({})

  const carregar = useCallback(() => {
    requisitar<Viatura[]>('/logistica/api/viaturas')
      .then(setViaturas)
      .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
    if (mostrarLegado) {
      requisitar<LegadoViatura[]>('/logistica/api/diagnostico/legado')
        .then((linhas) => setLegado(Object.fromEntries(linhas.map((l) => [l.id_viatura, l]))))
        .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
    }
  }, [mostrarLegado])

  useEffect(carregar, [carregar, sinalRecarga])

  async function movimentar(e: React.FormEvent) {
    e.preventDefault()
    if (idViatura === '') {
      setAviso({ tipo: 'erro', texto: 'Selecione a viatura.' })
      return
    }
    setEnviando(true)
    setAviso(null)
    try {
      // OPM vazia é enviada mesmo assim: quem valida é o backend (RF03).
      const viatura = await requisitar<Viatura>(`/logistica/api/viaturas/${idViatura}/movimentar`, {
        method: 'POST',
        body: JSON.stringify({ id_opm_destino: opm?.id_opm ?? null }),
      })
      setAviso({ tipo: 'sucesso', texto: `Viatura ${viatura.placa} lotada em ${viatura.nome_opm}.` })
      setOpm(null)
      carregar()
      onMovimentada()
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação.' })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="painel">
      <header className="painel-titulo">
        <span className="sistema">Sistema de Logística</span>
        <h2>Movimentação de viaturas</h2>
      </header>

      <form className="formulario" onSubmit={movimentar}>
        <label>
          Viatura
          <select value={idViatura} onChange={(e) => setIdViatura(e.target.value ? Number(e.target.value) : '')}>
            <option value="">Selecione…</option>
            {viaturas.map((v) => (
              <option key={v.id_viatura} value={v.id_viatura}>
                {v.placa} · {v.modelo} · {v.status_operacional}
              </option>
            ))}
          </select>
        </label>
        <label>
          OPM de destino
          <SeletorOpm valor={opm} onChange={setOpm} incluirInativas={incluirInativas} />
        </label>
        <label className="demo">
          <input type="checkbox" checked={incluirInativas} onChange={(e) => setIncluirInativas(e.target.checked)} />
          Demonstração: listar também OPMs inativas (para testar o bloqueio)
        </label>
        <button type="submit" disabled={enviando}>
          {enviando ? 'Gravando…' : 'Movimentar'}
        </button>
        {aviso && (
          <div role="alert" className={`aviso aviso-${aviso.tipo}`}>
            {aviso.texto}
          </div>
        )}
      </form>

      <label className="demo alternar-legado">
        <input type="checkbox" checked={mostrarLegado} onChange={(e) => setMostrarLegado(e.target.checked)} />
        Demonstração: mostrar unidade do cadastro antigo
      </label>
      {mostrarLegado && (
        <p className="nota">
          Colunas do cadastro antigo, exibidas só para entender o problema. Em produção ficam ocultas (RNF02).
          A ligação com a OPM é feita pelo nome da unidade antiga, associado na aba Implantação.
        </p>
      )}

      <div className="rolagem">
        <table>
          <thead>
            <tr>
              <th>Placa</th>
              <th>Modelo</th>
              <th>Status</th>
              {mostrarLegado && <th className="col-legado">Unidade antiga (legado)</th>}
              {mostrarLegado && <th className="col-legado">Associação com OPM</th>}
              <th>Unidade (OPM)</th>
            </tr>
          </thead>
          <tbody>
            {viaturas.map((v) => (
              <tr key={v.id_viatura}>
                <td className="placa">{v.placa}</td>
                <td>{v.modelo}</td>
                <td>
                  <span className={`selo selo-${v.status_operacional.toLowerCase()}`}>{v.status_operacional}</span>
                </td>
                {mostrarLegado && <UnidadeLegado legado={legado[v.id_viatura]} />}
                {mostrarLegado && <DePara legado={legado[v.id_viatura]} idOpmAtual={v.id_opm} />}
                <td>
                  {v.nome_opm ?? <span className="selo selo-erro">Sem unidade: invisível no Cautela</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function UnidadeLegado({ legado }: { legado?: LegadoViatura }) {
  const codigo = legado?.cd_unidade_legado?.trim()
  if (!codigo) return <td className="col-legado suave">(vazio)</td>
  return (
    <td className="col-legado">
      <span className="placa">{codigo}</span>{' '}
      {legado?.ds_unidade_legado ?? <span className="selo selo-erro">código inexistente no cadastro antigo</span>}
    </td>
  )
}

const ROTULO_DE_PARA = {
  CONFIRMADO: { classe: 'selo-disponivel', texto: 'Confirmado' },
  PENDENTE: { classe: 'selo-manutencao', texto: 'Sugestão a confirmar' },
  SEM_CORRESPONDENCIA: { classe: 'selo-erro', texto: 'Sem sugestão: escolha a OPM' },
}

function DePara({ legado, idOpmAtual }: { legado?: LegadoViatura; idOpmAtual: number | null }) {
  if (!legado?.cd_unidade_legado?.trim() || !legado.ds_unidade_legado) return <td className="col-legado suave">n/a</td>
  if (!legado.situacao_de_para) return <td className="col-legado suave">ainda não gerada</td>
  const rotulo = ROTULO_DE_PARA[legado.situacao_de_para]
  const diverge =
    legado.situacao_de_para === 'CONFIRMADO' &&
    idOpmAtual !== null &&
    idOpmAtual !== 0 &&
    idOpmAtual !== legado.id_opm_de_para
  return (
    <td className="col-legado">
      <span className={`selo ${rotulo.classe}`}>{rotulo.texto}</span>
      {legado.nome_opm_de_para && (
        <div className="suave">
          {legado.situacao_de_para === 'PENDENTE' ? 'Sugestão: ' : '→ '}
          {legado.nome_opm_de_para}
          {legado.situacao_de_para === 'PENDENTE' && legado.score !== null && ` (semelhança ${Math.round(legado.score * 100)}%)`}
        </div>
      )}
      {diverge && <span className="selo selo-erro">Diverge da coluna nova</span>}
    </td>
  )
}
