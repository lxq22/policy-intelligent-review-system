const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface StreamEvent<T = Record<string, unknown>> {
  event: string
  data: T
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const body = await response.json()
      message = body.error?.message || body.detail || message
    } catch {
      // 保留通用错误信息。
    }
    throw new ApiError(response.status, message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function jsonBody(value: unknown): Pick<RequestInit, 'body'> {
  return { body: JSON.stringify(value) }
}

export async function streamApi<T = Record<string, unknown>>(
  path: string,
  options: RequestInit,
  onEvent: (event: StreamEvent<T>) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: { Accept: 'text/event-stream', ...options.headers },
  })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const body = await response.json()
      message = body.error?.message || body.detail || message
    } catch {
      // 保留通用错误信息。
    }
    throw new ApiError(response.status, message)
  }
  if (!response.body) throw new Error('浏览器无法读取审查进度')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const consume = (block: string) => {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (dataLines.length) onEvent({ event, data: JSON.parse(dataLines.join('\n')) as T })
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''
    blocks.forEach(consume)
    if (done) break
  }
  if (buffer.trim()) consume(buffer)
}
