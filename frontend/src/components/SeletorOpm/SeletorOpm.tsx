import { useState } from 'react'
import type { Opm } from '../../types'
import { useOpms } from './useOpms'

interface Props {
  valor: Opm | null
  onChange: (opm: Opm | null) => void
  incluirInativas?: boolean
}

/** Combobox de OPMs com busca. Único componente que sabe de onde vêm as OPMs. */
export function SeletorOpm({ valor, onChange, incluirInativas = false }: Props) {
  const [texto, setTexto] = useState('')
  const [aberto, setAberto] = useState(false)
  const [destaque, setDestaque] = useState(0)
  const { opms, carregando } = useOpms(valor ? '' : texto, incluirInativas)

  function selecionar(opm: Opm) {
    onChange(opm)
    // O nome exibido vem de `valor`; limpar o texto faz o campo esvaziar quando o pai zera a seleção.
    setTexto('')
    setAberto(false)
  }

  function aoDigitar(novo: string) {
    setTexto(novo)
    setDestaque(0)
    setAberto(true)
    if (valor) onChange(null)
  }

  function aoTeclar(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setAberto(true)
      setDestaque((i) => Math.min(i + 1, opms.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setDestaque((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && aberto && opms[destaque]) {
      e.preventDefault()
      selecionar(opms[destaque])
    } else if (e.key === 'Escape') {
      setAberto(false)
    }
  }

  return (
    <div className="seletor">
      <input
        role="combobox"
        aria-expanded={aberto}
        aria-controls="lista-opms"
        placeholder="Digite para buscar a OPM de destino"
        value={valor ? valor.nome : texto}
        onChange={(e) => aoDigitar(e.target.value)}
        onFocus={() => setAberto(true)}
        onBlur={() => setTimeout(() => setAberto(false), 150)}
        onKeyDown={aoTeclar}
      />
      {aberto && !valor && (
        <ul id="lista-opms" role="listbox" className="seletor-lista">
          {carregando && <li className="seletor-vazio">Buscando…</li>}
          {!carregando && opms.length === 0 && <li className="seletor-vazio">Nenhuma OPM encontrada</li>}
          {!carregando &&
            opms.map((opm, i) => (
              <li
                key={opm.id_opm}
                role="option"
                aria-selected={i === destaque}
                className={i === destaque ? 'destaque' : undefined}
                onMouseDown={() => selecionar(opm)}
              >
                {opm.nome}
                {opm.status !== 'ATIVA' && <span className="selo selo-erro">{opm.status}</span>}
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}
