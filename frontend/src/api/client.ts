export class ErroApi extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export async function requisitar<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const corpo = await resp.json().catch(() => null)
  if (!resp.ok) {
    const detalhe = typeof corpo?.detail === 'string' ? corpo.detail : `Erro ${resp.status}`
    throw new ErroApi(resp.status, detalhe)
  }
  return corpo as T
}
