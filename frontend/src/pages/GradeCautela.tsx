import { useCallback, useEffect, useState } from 'react'
import { requisitar } from '../api/client'
import type { FrotaDisponivel, P4 } from '../types'

interface Props {
  sinalRecarga: number
}

/** Tela do Sistema de Cautela: grade de viaturas disponíveis para o P4 "logado". */
export function GradeCautela({ sinalRecarga }: Props) {
  const [usuarios, setUsuarios] = useState<P4[]>([])
  const [login, setLogin] = useState('p4.opm1')
  const [frota, setFrota] = useState<FrotaDisponivel | null>(null)
  const [atualizadoEm, setAtualizadoEm] = useState<Date | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    requisitar<P4[]>('/cautela/api/p4').then(setUsuarios).catch(() => setUsuarios([]))
  }, [])

  // Recarrega ao abrir a tela, ao trocar de P4 e após cada movimentação (RF02).
  const carregar = useCallback(() => {
    requisitar<FrotaDisponivel>('/cautela/api/frota/disponivel', { headers: { 'X-Usuario-P4': login } })
      .then((dados) => {
        setFrota(dados)
        setAtualizadoEm(new Date())
        setErro(null)
      })
      .catch((e: Error) => setErro(e.message))
  }, [login])

  useEffect(carregar, [carregar, sinalRecarga])

  return (
    <section className="painel">
      <header className="painel-titulo">
        <span className="sistema sistema-cautela">Sistema de Cautela</span>
        <h2>Viaturas disponíveis para cautela</h2>
      </header>

      <div className="formulario">
        <label>
          P4 autenticado (simulação de login)
          <select value={login} onChange={(e) => setLogin(e.target.value)}>
            {usuarios.map((u) => (
              <option key={u.login} value={u.login}>
                {u.login} · {u.nome_opm}
              </option>
            ))}
          </select>
        </label>
        <div className="linha">
          <button type="button" className="secundario" onClick={carregar}>
            Recarregar
          </button>
          {atualizadoEm && <small>Atualizado às {atualizadoEm.toLocaleTimeString('pt-BR')}</small>}
        </div>
        {erro && (
          <div role="alert" className="aviso aviso-erro">
            {erro}
          </div>
        )}
      </div>

      {frota && (
        <>
          <p className="resumo">
            <strong>{frota.p4.nome_opm}</strong>: {frota.viaturas.length} viatura(s) disponível(is)
          </p>
          <table>
            <thead>
              <tr>
                <th>Placa</th>
                <th>Modelo</th>
              </tr>
            </thead>
            <tbody>
              {frota.viaturas.map((v) => (
                <tr key={v.id_viatura}>
                  <td className="placa">{v.placa}</td>
                  <td>{v.modelo}</td>
                </tr>
              ))}
              {frota.viaturas.length === 0 && (
                <tr>
                  <td colSpan={2} className="vazio">
                    Nenhuma viatura disponível para esta OPM.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
