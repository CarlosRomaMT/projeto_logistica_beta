import { useEffect, useState } from 'react'
import { requisitar } from '../../api/client'
import type { Opm } from '../../types'

const ATRASO_MS = 300

/** Busca OPMs na API oficial com debounce. */
export function useOpms(termo: string, incluirInativas: boolean) {
  const [opms, setOpms] = useState<Opm[]>([])
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    let cancelado = false
    setCarregando(true)
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ q: termo, incluir_inativas: String(incluirInativas) })
      requisitar<Opm[]>(`/logistica/api/opms?${params}`)
        .then((dados) => !cancelado && setOpms(dados))
        .catch(() => !cancelado && setOpms([]))
        .finally(() => !cancelado && setCarregando(false))
    }, ATRASO_MS)
    return () => {
      cancelado = true
      clearTimeout(timer)
    }
  }, [termo, incluirInativas])

  return { opms, carregando }
}
