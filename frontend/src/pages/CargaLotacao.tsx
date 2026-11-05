import { useCallback, useEffect, useState } from 'react'
import { ErroApi, requisitar } from '../api/client'
import { AVISO_SEM_REVISOR, EtapaTitulo } from '../components/EtapaTitulo/EtapaTitulo'
import type { ResultadoCarga } from '../types'

interface Props {
  revisor: string
  pedirRevisor: () => void
  sinalRecarga: number
  onAlterado: () => void
}

type Aviso = { tipo: 'sucesso' | 'erro'; texto: string }

export const MOTIVO: Record<string, string> = {
  DE_PARA_PENDENTE_VALIDACAO: 'Unidade antiga ainda não associada (etapa 1)',
  SEM_CORRESPONDENCIA: 'Unidade antiga sem OPM correspondente',
  OPM_INATIVA: 'Unidade antiga associada a uma OPM inativa',
  LEGADO_NULO: 'Sem unidade no cadastro antigo',
  UNIDADE_LEGADO_INEXISTENTE: 'Código de unidade antiga inexistente',
  DIVERGENCIA_LEGADO_X_NOVO: 'Divergência: vira proposta de correção (etapa 3)',
}

/** Carga em lote (RF04) pela tela: simula, mostra o efeito e só então permite gravar. */
export function CargaLotacao({ revisor, pedirRevisor, sinalRecarga, onAlterado }: Props) {
  const [aguardando, setAguardando] = useState<number | null>(null)
  const [resultado, setResultado] = useState<ResultadoCarga | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [aviso, setAviso] = useState<Aviso | null>(null)
  const [gravadaEm, setGravadaEm] = useState('')

  const carregar = useCallback(() => {
    requisitar<{ aguardando_carga: number }>('/logistica/api/carga')
      .then((dados) => setAguardando(dados.aguardando_carga))
      .catch((e: Error) => setAviso({ tipo: 'erro', texto: e.message }))
    // Uma simulação antiga pode não valer mais depois de outra alteração.
    setResultado((atual) => (atual?.simulacao ? null : atual))
  }, [])

  useEffect(carregar, [carregar, sinalRecarga])

  useEffect(() => {
    if (revisor.trim()) setAviso((a) => (a?.texto === AVISO_SEM_REVISOR ? null : a))
  }, [revisor])

  async function executar(acao: 'simular' | 'executar') {
    if (acao === 'executar' && !revisor.trim()) {
      setAviso({ tipo: 'erro', texto: AVISO_SEM_REVISOR })
      pedirRevisor()
      return
    }
    setOcupado(true)
    setAviso(null)
    try {
      const r = await requisitar<ResultadoCarga>(`/logistica/api/carga/${acao}`, {
        method: 'POST',
        body: acao === 'executar' ? JSON.stringify({ usuario: revisor.trim() }) : undefined,
      })
      setResultado(r)
      if (acao === 'executar') setGravadaEm(new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }))
      if (acao === 'executar') {
        setAviso({
          tipo: 'sucesso',
          texto: `Carga gravada: ${r.lotadas.length} viatura(s) lotada(s) na OPM correta e ${r.contingencia} na OPM 0.`,
        })
        onAlterado()
      }
    } catch (erro) {
      setAviso({ tipo: 'erro', texto: erro instanceof ErroApi ? erro.message : 'Falha de comunicação.' })
    } finally {
      setOcupado(false)
    }
  }

  const simulacao = resultado?.simulacao ?? false
  const divergencias = resultado?.inconformidades.filter((i) => i.motivo === 'DIVERGENCIA_LEGADO_X_NOVO').length ?? 0

  return (
    <section className="painel">
      <EtapaTitulo
        numero={2}
        titulo="Carga da lotação"
        situacao={aguardando === null ? null : aguardando ? `${aguardando} viatura(s) aguardando` : 'Concluída'}
        pendente={!!aguardando}
      />
      <p className="nota">
        Lota as viaturas nas OPMs associadas na etapa 1; as de unidades ainda não associadas vão para a OPM 0
        (contingência). A divergência entre o cadastro antigo e o novo vira proposta de
        correção (etapa 3). Tudo numa única transação.
      </p>
      <p className="resumo">
        {aguardando === null
          ? 'Consultando…'
          : aguardando
            ? <><strong>{aguardando}</strong> viatura(s) ativa(s) ainda sem OPM: invisíveis no Cautela até a carga.</>
            : 'Nenhuma viatura ativa aguardando a carga. Rodar de novo só reavalia as que estão na OPM 0.'}
      </p>
      <div className="linha">
        <button type="button" className="secundario" onClick={() => executar('simular')} disabled={ocupado}>
          Simular
        </button>
        <button
          type="button"
          onClick={() => executar('executar')}
          disabled={ocupado || !resultado?.simulacao}
        >
          Executar carga
        </button>
      </div>
      {!!aguardando && !resultado?.simulacao && (
        <small className="suave">Clique em Simular primeiro: Executar carga é liberado depois que você vê o efeito.</small>
      )}
      {aviso && (
        <div role="alert" className={`aviso aviso-${aviso.tipo}`}>
          {aviso.texto}
        </div>
      )}

      {resultado && (
        <>
          <h3>{resultado.simulacao ? 'Simulação (nada foi gravado)' : `Resultado da carga gravada às ${gravadaEm}`}</h3>
          {!resultado.simulacao && (
            <p className="suave">
              Retrato do momento da carga. O que ainda falta resolver está nas etapas 3 e 4, que se atualizam sozinhas.
            </p>
          )}
          <ul className="resumo-carga">
            <li>
              <span className="selo selo-disponivel">{resultado.lotadas.length}</span>{' '}
              {simulacao ? 'serão lotadas' : 'foram lotadas'} na OPM correta, pela associação da etapa 1
            </li>
            <li>
              <span className="selo selo-manutencao">{resultado.contingencia}</span>{' '}
              {simulacao ? 'ficarão' : 'ficaram'} na OPM 0 (contingência), sem OPM definida: lote-as na etapa 4
            </li>
            {divergencias > 0 && (
              <li>
                <span className="selo selo-manutencao">{divergencias}</span> com divergência entre o cadastro antigo e o
                novo: {simulacao ? 'não serão alteradas' : 'não foram alteradas'}, decida na etapa 3
              </li>
            )}
            {resultado.de_para_criados > 0 && (
              <li>
                <span className="selo">{resultado.de_para_criados}</span> unidade(s) antiga(s) nova(s) entraram na etapa 1
              </li>
            )}
          </ul>
          {resultado.relatorio && (
            <p className="resumo">
              <a href={`/logistica/api/carga/relatorios/${resultado.relatorio}`} download>
                Baixar relatório das que precisam de atenção (CSV)
              </a>
            </p>
          )}

          <h3>
            {simulacao ? 'Serão lotadas' : 'Lotadas'} na OPM correta ({resultado.lotadas.length})
          </h3>
          <div className="rolagem">
            <table>
              <thead>
                <tr>
                  <th>Placa</th>
                  <th>Unidade antiga</th>
                  <th>OPM</th>
                </tr>
              </thead>
              <tbody>
                {resultado.lotadas.map((l) => (
                  <tr key={l.placa}>
                    <td className="placa">{l.placa}</td>
                    <td>
                      <span className="placa">{l.cd_unidade_legado}</span> {l.ds_unidade_legado}
                    </td>
                    <td>{l.nome_opm}</td>
                  </tr>
                ))}
                {resultado.lotadas.length === 0 && (
                  <tr>
                    <td colSpan={3} className="vazio">
                      Nenhuma viatura a lotar.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <h3>Precisam de atenção ({resultado.inconformidades.length})</h3>
          <div className="rolagem">
            <table>
              <thead>
                <tr>
                  <th>Placa</th>
                  <th>Unidade antiga</th>
                  <th>Motivo</th>
                  <th>Sugestão</th>
                </tr>
              </thead>
              <tbody>
                {resultado.inconformidades.map((i) => (
                  <tr key={`${i.placa}-${i.motivo}`}>
                    <td className="placa">{i.placa}</td>
                    <td>
                      <span className="placa">{i.cd_unidade_legado?.trim() || '—'}</span> {i.ds_unidade_legado}
                    </td>
                    <td>{MOTIVO[i.motivo] ?? i.motivo}</td>
                    <td className="suave">{i.opm_sugerida}</td>
                  </tr>
                ))}
                {resultado.inconformidades.length === 0 && (
                  <tr>
                    <td colSpan={4} className="vazio">
                      Nenhuma viatura precisa de atenção.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
