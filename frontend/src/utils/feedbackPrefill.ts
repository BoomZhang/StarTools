import type { ApiErrorInfo } from '@/api/client'

export interface FeedbackPrefill {
  toolCode?: string
  errorCode?: string
  taskId?: string
  path?: string
}

const KEY = 'startools:feedback-prefill:v1'

export function setFeedbackPrefill(data: FeedbackPrefill): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(data))
  } catch {
    // 忽略会话存储异常
  }
}

export function takeFeedbackPrefill(): FeedbackPrefill | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    sessionStorage.removeItem(KEY)
    return JSON.parse(raw) as FeedbackPrefill
  } catch {
    return null
  }
}

export function errorFeedbackPrefill(
  toolCode: string,
  error: ApiErrorInfo | null,
  path?: string,
): FeedbackPrefill {
  return {
    toolCode,
    errorCode: error?.code,
    taskId: error?.taskId,
    path: path || window.location.pathname,
  }
}
