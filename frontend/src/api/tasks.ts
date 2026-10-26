import type { ServerTask } from '@/types'
import { api } from './client'

export interface CreateTaskOptions {
  onUploadProgress?: (percent: number) => void
  isRetry?: boolean
}

export async function createServerTask(
  toolCode: string,
  files: File[],
  params: Record<string, unknown>,
  options: CreateTaskOptions = {},
): Promise<ServerTask> {
  const form = new FormData()
  form.append('tool_code', toolCode)
  form.append('params', JSON.stringify(params))
  form.append('is_retry', options.isRetry ? 'true' : 'false')
  for (const file of files) form.append('files', file, file.name)

  const { data } = await api.post<ServerTask>('/tasks', form, {
    timeout: 300000,
    onUploadProgress: (event) => {
      if (!options.onUploadProgress) return
      if (event.total) {
        options.onUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
      }
    },
  })
  return data
}

export async function fetchServerTask(taskId: string): Promise<ServerTask> {
  const { data } = await api.get<ServerTask>(`/tasks/${taskId}`)
  return data
}

export async function deleteTaskResults(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}/results`)
}

export function archiveUrl(taskId: string): string {
  return `/api/tasks/${taskId}/archive`
}
