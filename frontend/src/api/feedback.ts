import { api } from './client'

export interface UsageReport {
  tool_code: string
  result: 'succeeded' | 'partial' | 'failed' | 'canceled'
  duration_ms: number
  file_count?: number
  total_size?: number
  error_code?: string
  is_retry?: boolean
}

export async function reportUsage(payload: UsageReport): Promise<void> {
  try {
    await api.post('/usage', payload)
  } catch {
    // 使用记录失败不影响访客任务结果
  }
}

export interface FeedbackPayload {
  type: string
  tool_code?: string | null
  description: string
  expected?: string
  contact?: string
  context?: {
    path?: string
    tool_code?: string
    task_id?: string
    error_code?: string
    browser?: string
    viewport?: string
  }
}

export async function submitFeedback(payload: FeedbackPayload) {
  const { data } = await api.post('/feedback', payload)
  return data as { number: string; created_at: string; message: string }
}
