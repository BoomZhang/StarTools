import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
})

export interface ApiErrorInfo {
  status: number | null
  code?: string
  message: string
  retryAt?: string | null
  taskId?: string
}

export function parseApiError(error: unknown): ApiErrorInfo {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') {
      return { status: null, message: '请求超时，请检查网络后重试' }
    }
    if (error.response) {
      const detail = error.response.data?.detail
      if (typeof detail === 'string') {
        return { status: error.response.status, message: detail }
      }
      if (detail && typeof detail === 'object') {
        return {
          status: error.response.status,
          code: detail.code,
          message: detail.message || '请求未成功',
          retryAt: detail.retry_at,
          taskId: detail.task_id,
        }
      }
      return { status: error.response.status, message: `请求未成功（HTTP ${error.response.status}）` }
    }
    return { status: null, message: '无法连接服务，请检查网络或稍后重试' }
  }
  return { status: null, message: error instanceof Error ? error.message : String(error) }
}

export function absoluteApiPath(path: string): string {
  if (path.startsWith('http')) return path
  if (path.startsWith(API_BASE_URL)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}
