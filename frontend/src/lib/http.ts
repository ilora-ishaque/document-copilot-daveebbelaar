const DEFAULT_TIMEOUT_MS = 30_000

export interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: unknown
  timeoutMs?: number
  signal?: AbortSignal
}

export class ApiError extends Error {
  readonly status: number | null
  readonly isNetworkError: boolean
  readonly body: unknown

  constructor(
    message: string,
    options: { status: number | null; isNetworkError: boolean; body?: unknown },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status
    this.isNetworkError = options.isNetworkError
    this.body = options.body
  }
}

export async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', headers = {}, body, timeoutMs = DEFAULT_TIMEOUT_MS, signal } = options

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  signal?.addEventListener('abort', () => controller.abort(), { once: true })

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (error) {
    throw new ApiError(networkErrorMessage(error), { status: null, isNetworkError: true })
  } finally {
    clearTimeout(timeoutId)
  }

  const responseBody = await parseBody(response)

  if (!response.ok) {
    throw new ApiError(errorMessage(responseBody, response), {
      status: response.status,
      isNetworkError: false,
      body: responseBody,
    })
  }

  return responseBody as T
}

function networkErrorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request timed out'
  }
  return 'Network request failed'
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const text = await response.text()
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function errorMessage(body: unknown, response: Response): string {
  if (
    body !== null &&
    typeof body === 'object' &&
    'detail' in body &&
    typeof body.detail === 'string'
  ) {
    return body.detail
  }
  return `Request failed with status ${response.status}`
}
