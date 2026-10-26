import type { SitePayload, Tool } from '@/types'
import { api } from './client'

export async function fetchSite(): Promise<SitePayload> {
  const { data } = await api.get<SitePayload>('/site')
  return data
}

export async function fetchTool(slug: string): Promise<{ tool: Tool }> {
  const { data } = await api.get<{ tool: Tool }>(`/tools/${slug}`)
  return data
}
