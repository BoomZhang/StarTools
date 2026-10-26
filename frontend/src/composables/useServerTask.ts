import { computed, ref } from 'vue'

import { parseApiError, type ApiErrorInfo } from '@/api/client'
import { createServerTask, deleteTaskResults, fetchServerTask } from '@/api/tasks'
import type { ServerTask } from '@/types'

export type TaskState =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'succeeded'
  | 'partial'
  | 'failed'
  | 'canceled'
  | 'expired'

const SESSION_LIMIT = 60 * 60 * 1000

export function useServerTask(toolCode: string) {
  const state = ref<TaskState>('idle')
  const progress = ref(0)
  const task = ref<ServerTask | null>(null)
  const error = ref<ApiErrorInfo | null>(null)
  const restoring = ref(false)

  const busy = computed(() => state.value === 'uploading' || state.value === 'processing')

  function sessionKey(): string {
    return `startools:task:${toolCode}`
  }

  function remember(id: string): void {
    try {
      sessionStorage.setItem(sessionKey(), JSON.stringify({ id, at: Date.now() }))
    } catch {
      // 忽略会话存储异常
    }
  }

  function forget(): void {
    try {
      sessionStorage.removeItem(sessionKey())
    } catch {
      // 忽略会话存储异常
    }
  }

  async function run(
    files: File[],
    params: Record<string, unknown>,
    options: { isRetry?: boolean } = {},
  ): Promise<void> {
    if (busy.value) return
    error.value = null
    task.value = null
    progress.value = 0
    state.value = 'uploading'

    try {
      const data = await createServerTask(toolCode, files, params, {
        isRetry: options.isRetry,
        onUploadProgress: (percent) => {
          progress.value = percent
          if (percent >= 100) state.value = 'processing'
        },
      })
      progress.value = 100
      task.value = data
      state.value = data.status === 'processing' ? 'processing' : data.status
      remember(data.task_id)
    } catch (err) {
      error.value = parseApiError(err)
      state.value = 'failed'
      if (error.value.taskId) remember(error.value.taskId)
    }
  }

  async function restore(): Promise<void> {
    let raw: string | null = null
    try {
      raw = sessionStorage.getItem(sessionKey())
    } catch {
      return
    }
    if (!raw) return
    try {
      const saved = JSON.parse(raw) as { id?: string; at?: number }
      if (!saved.id || !saved.at || Date.now() - saved.at > SESSION_LIMIT) {
        forget()
        return
      }
      restoring.value = true
      const data = await fetchServerTask(saved.id)
      task.value = data
      state.value = data.status
      progress.value = 100
      if (data.status === 'expired') forget()
    } catch (err) {
      const info = parseApiError(err)
      if (info.status === 404 || info.status === 410) forget()
    } finally {
      restoring.value = false
    }
  }

  async function removeResults(): Promise<void> {
    if (!task.value) return
    try {
      await deleteTaskResults(task.value.task_id)
      task.value = { ...task.value, results: [] }
      forget()
      state.value = 'idle'
    } catch (err) {
      error.value = parseApiError(err)
    }
  }

  function reset(): void {
    state.value = 'idle'
    progress.value = 0
    task.value = null
    error.value = null
  }

  return { state, progress, task, error, busy, restoring, run, restore, removeResults, reset, forget }
}
