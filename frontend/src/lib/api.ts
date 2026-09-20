import { env } from '@/lib/env'
import { ApiError, request, type RequestOptions } from '@/lib/http'
import { supabase } from '@/lib/supabase'

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function call<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = { ...(await authHeaders()), ...options.headers }
  return request<T>(`${env.apiBaseUrl}${path}`, { ...options, headers })
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => call<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    call<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    call<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    call<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    call<T>(path, { ...options, method: 'DELETE' }),
}

export { ApiError }
